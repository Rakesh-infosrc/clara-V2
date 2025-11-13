"""
Virtual Receptionist Flow Manager

This module implements the complete flow logic based on the provided flowchart:
1. Wake Word Detection → Employee/Visitor Classification
2. Employee Path: Face Recognition → Manual Verification → Face Registration
3. Visitor Path: Information Collection → Host Notification → Face Capture
4. Tool Access Control → Flow Completion
"""

import time
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from language_utils import (
    get_message,
    resolve_language_code,
    SUPPORTED_LANGUAGES,
    normalize_transcript,
    detect_language_from_text,
)
from tools.config import is_face_recognition_enabled
from agent_state import get_preferred_language, set_preferred_language


class FlowState(Enum):
    """Flow states matching the flowchart"""
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LANGUAGE_SELECTION = "language_selection"
    USER_CLASSIFICATION = "user_classification"
    FACE_RECOGNITION = "face_recognition"
    FACE_MATCH_CHECK = "face_match_check"
    MANUAL_VERIFICATION = "manual_verification"
    CREDENTIAL_CHECK = "credential_check"
    FACE_REGISTRATION = "face_registration"
    EMPLOYEE_VERIFIED = "employee_verified"
    VISITOR_INFO_COLLECTION = "visitor_info_collection"
    VISITOR_FACE_CAPTURE = "visitor_face_capture"
    HOST_NOTIFICATION = "host_notification"
    TOOL_ACCESS = "tool_access"
    FLOW_END = "flow_end"


class UserType(Enum):
    """User types from the flowchart"""
    EMPLOYEE = "employee"
    VISITOR = "visitor"
    UNKNOWN = "unknown"


@dataclass
class FlowSession:
    """Session data for tracking user flow progress"""
    session_id: str
    current_state: FlowState
    user_type: UserType
    start_time: float
    last_activity: float
    verification_attempts: int
    user_data: Dict[str, Any]
    is_verified: bool
    verification_method: Optional[str] = None


class VirtualReceptionistFlow:
    """Main flow manager implementing the flowchart logic"""
    
    def __init__(self):
        self.sessions: Dict[str, FlowSession] = {}
        self.current_session_id: Optional[str] = None
        self.load_sessions()
    
    def create_session(self, session_id: str = None) -> str:
        """Create a new flow session"""
        if session_id is None:
            session_id = f"session_{int(time.time() * 1000)}"
        
        session = FlowSession(
            session_id=session_id,
            current_state=FlowState.IDLE,
            user_type=UserType.UNKNOWN,
            start_time=time.time(),
            last_activity=time.time(),
            verification_attempts=0,
            user_data={},
            is_verified=False
        )
        
        self.sessions[session_id] = session
        self.current_session_id = session_id
        self.save_sessions()
        return session_id
    
    def get_current_session(self) -> Optional[FlowSession]:
        """Get the current active session"""
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        return None
    def process_wake_word_detected(self) -> Tuple[bool, str]:
        """Process wake word detection - start of flow"""
        # Create new session or reset existing one
        self.create_session()
        session = self.get_current_session()

        if session:
            session.current_state = FlowState.LANGUAGE_SELECTION
            session.last_activity = time.time()

        self.save_sessions()
        # Return localized greeting. The caller (agent/frontend) will append the wake prompt.
        lang = get_preferred_language()
        greeting = get_message("wake_intro", lang)
        language_prompt = get_message("language_selection_prompt", lang)
        combined = f"{greeting} {language_prompt}"
        print(f"[Flow] Wake message ({lang}): {combined}")
        return True, combined
    
    def process_user_classification(self, user_input: str) -> Tuple[bool, str, FlowState]:
        """Process user type classification"""
        session = self.get_current_session()
        if not session:
            # Create a new session if none exists
            print("[Flow] No session found, creating new session for classification")
            self.create_session()
            session = self.get_current_session()
            if not session:
                lang = get_preferred_language()
                return False, get_message("manual_no_session", lang), FlowState.IDLE

        lang = get_preferred_language()
        user_input_clean = user_input.strip()
        user_input_normalized = normalize_transcript(user_input_clean, lang)
        user_input_lower = user_input_normalized.lower()
        
        print(f"[Flow] Processing classification - Current state: {session.current_state.value}, Input: '{user_input_lower}'")

        # Check for employee/visitor keywords first, regardless of current state
        # This allows users to skip language selection if they directly say "I'm an employee"
        employee_keywords = [
            'employee', 'staff', 'worker', 'work here', 'i am an employee', 
            'am an employee', 'i work here', 'am a employee', 'i am a employee',
            'ஊழியர்', 'ஊழியன', 'ஊழியர்கள்',
            'ఉద్యోగి', 'సిబ్బంది',
            'कर्मचारी', 'स्टाफ'
        ]
        visitor_keywords = [
            'visitor', 'guest', 'visiting', 'meeting',
            'வருகையாளர்', 'விருந்தினர்', 'வருகை',
            'సందర్శకుడు', 'అతిథి',
            'आगंतुक', 'मेहमान'
        ]
        
        # Check if user is directly stating they're an employee or visitor
        is_employee_intent = any(word in user_input_lower for word in employee_keywords)
        is_visitor_intent = any(word in user_input_lower for word in visitor_keywords)

        # Allow users to clarify or change their preferred language even after reaching
        # the classification step (e.g., "I am saying Telugu"). Only treat the input as a
        # language switch when no employee/visitor intent is detected to avoid interrupting
        # the normal flow.
        language_switch = detect_language_from_text(user_input_lower)
        if (
            language_switch in SUPPORTED_LANGUAGES
            and language_switch != lang
            and not is_employee_intent
            and not is_visitor_intent
        ):
            print(f"[Flow] Language switch detected during classification: {language_switch}")
            set_preferred_language(language_switch)
            session.current_state = FlowState.USER_CLASSIFICATION
            session.last_activity = time.time()
            self.save_sessions()

            response = get_message("language_selection_confirmed", language_switch)
            print(f"[Flow] Language re-confirmed ({language_switch}): '{response}'")
            return True, response, FlowState.USER_CLASSIFICATION
        
        if is_employee_intent:
            print(f"🎯 [Flow] Employee intent detected directly: '{user_input_lower}'")
            session.user_type = UserType.EMPLOYEE
            session.current_state = FlowState.FACE_RECOGNITION
            session.last_activity = time.time()
            response = get_message("classification_employee", lang)
            # Signal frontend to start face capture
            try:
                from flow_signal import post_signal
                print(f"🚀 Posting start_face_capture signal for employee classification")
                post_signal("start_face_capture", {
                    "message": response,
                    "next_endpoint": "/flow/face_recognition"
                })
                print(f"✅ Successfully posted start_face_capture signal")
            except Exception as e:
                print(f"❌ Warning: could not post start_face_capture signal: {e}")
            self.save_sessions()
            print(f"[Flow] Classified as EMPLOYEE ({lang}): '{response}'")
            return True, response, FlowState.FACE_RECOGNITION
        
        if is_visitor_intent:
            print(f"🎯 [Flow] Visitor intent detected directly: '{user_input_lower}'")
            session.user_type = UserType.VISITOR
            session.current_state = FlowState.VISITOR_INFO_COLLECTION
            session.last_activity = time.time()
            response = get_message("classification_visitor", lang)
            try:
                from flow_signal import post_signal
                post_signal("start_visitor_info", {
                    "message": response,
                    "next_endpoint": "/flow/visitor_info"
                })
            except Exception as e:
                print(f"Warning: could not post start_visitor_info signal: {e}")
            self.save_sessions()
            print(f"[Flow] Classified as VISITOR ({lang}): '{response}'")
            return True, response, FlowState.VISITOR_INFO_COLLECTION

        if session.current_state == FlowState.LANGUAGE_SELECTION:
            lang_choice = resolve_language_code(user_input_lower)
            if lang_choice not in SUPPORTED_LANGUAGES:
                response = get_message("language_selection_retry", lang)
                print(f"[Flow] Language selection retry ({lang}): '{response}'")
                return False, response, FlowState.LANGUAGE_SELECTION

            set_preferred_language(lang_choice)
            session.current_state = FlowState.USER_CLASSIFICATION
            session.last_activity = time.time()
            self.save_sessions()

            response = get_message("language_selection_confirmed", lang_choice)
            print(f"[Flow] Language selected ({lang_choice}): '{response}'")
            return True, response, FlowState.USER_CLASSIFICATION

        # If unclear, ask for clarification
        response = get_message("classification_retry", lang)
        print(f"[Flow] Unclear classification ({lang}): '{response}'")
        return False, response, FlowState.USER_CLASSIFICATION
    
    def process_face_recognition_result(self, face_result: Dict[str, Any]) -> Tuple[bool, str, FlowState]:
        """Process face recognition results for employees"""
        session = self.get_current_session()

        # Recover from stale session issues (e.g. session ended just before recognition finished)
        if not session:
            self.create_session()
            session = self.get_current_session()

        if session and session.user_type != UserType.EMPLOYEE:
            # A valid face recognition success should promote the user to EMPLOYEE
            if face_result.get("status") == "success":
                session.user_type = UserType.EMPLOYEE
                session.current_state = FlowState.FACE_MATCH_CHECK
            else:
                # Gracefully fall back to manual verification instead of a hard error
                session.user_type = UserType.EMPLOYEE
                session.current_state = FlowState.MANUAL_VERIFICATION
                self.save_sessions()
                lang = get_preferred_language()
                return False, get_message("manual_face_not_recognized", lang), FlowState.MANUAL_VERIFICATION

        if not session:
            lang = get_preferred_language()
            return False, get_message("manual_invalid_session", lang), FlowState.IDLE

        if face_result.get("status") == "success":
            if not is_face_recognition_enabled():
                session.current_state = FlowState.MANUAL_VERIFICATION
                session.verification_attempts += 1
                self.save_sessions()
                lang = get_preferred_language()
                return (
                    False,
                    get_message("manual_face_not_recognized", lang),
                    FlowState.MANUAL_VERIFICATION,
                )
            # Face match found
            emp_name = (
                face_result.get("name")
                or face_result.get("employee_name")
                or session.user_data.get("employee_name")
            )
            emp_id = (
                face_result.get("employeeId")
                or face_result.get("employee_id")
                or session.user_data.get("employee_id")
            )

            if not emp_name or not emp_id:
                # Missing identity details – fall back to manual verification flow
                session.current_state = FlowState.MANUAL_VERIFICATION
                session.verification_attempts += 1
                self.save_sessions()
                lang = get_preferred_language()
                return False, get_message("manual_face_not_recognized", lang), FlowState.MANUAL_VERIFICATION

            session.user_data.update({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "verification_method": "face_recognition"
            })
            session.is_verified = True
            session.current_state = FlowState.EMPLOYEE_VERIFIED

            # Clear manual verification prompts if face recognition succeeded later
            session.user_data.pop("manual_name", None)
            session.user_data.pop("manual_employee_id", None)
            session.user_data.pop("manual_email", None)
            session.user_data.pop("manual_phone", None)

            # Update global verification state
            from agent_state import set_user_verified
            set_user_verified(emp_name, emp_id)

            self.save_sessions()
            lang = get_preferred_language()
            
            greeting_parts = [get_message("face_recognition_success", lang, name=emp_name)]
            
            # Check if there's an actual manager visit scheduled for today
            from datetime import datetime
            from tools.manager_visit_repository import get_manager_visit
            
            now = datetime.now()
            today = f"{now.year}-{now.month}-{now.day}"
            visit_record = get_manager_visit(emp_id, today)
            
            if visit_record:
                # Manager visit exists for today - show farewell message
                office = visit_record.get("office") or visit_record.get("Office") or "our office"
                greeting_parts.extend(
                    [
                        f"Hope you had a smooth and comfortable journey. It was wonderful having you at our {office} office.",
                        "We truly hope your visit was both memorable and meaningful.",
                        "Thanks so much for taking the time to be with us."
                    ]
                )

            return True, "\n".join(greeting_parts), FlowState.EMPLOYEE_VERIFIED
        else:
            # Face not matched - proceed to manual verification
            session.current_state = FlowState.MANUAL_VERIFICATION
            session.verification_attempts += 1
            self.save_sessions()
            lang = get_preferred_language()
            return False, get_message("manual_face_not_recognized", lang), FlowState.MANUAL_VERIFICATION
    
    def process_manual_verification_step(
        self,
        email: str = None,
        otp: str = None,
        name: str = None,
        employee_id: str = None,
    ) -> Tuple[bool, str, FlowState]:
        """Process manual employee verification steps"""
        session = self.get_current_session()
        if not session:
            lang = get_preferred_language()
            return False, get_message("manual_no_session", lang), FlowState.IDLE

        resolved_email = email

        if not employee_id:
            lang = get_preferred_language()
            return False, get_message("manual_missing_employee_id", lang), FlowState.MANUAL_VERIFICATION

        if not resolved_email and employee_id:
            try:
                from tools.employee_repository import get_employee_by_id

                record_by_id = get_employee_by_id(employee_id)
                if record_by_id:
                    resolved_email = record_by_id.get("email")
                    if resolved_email:
                        session.user_data.setdefault("manual_employee_id", record_by_id.get("employee_id"))
                        session.user_data.setdefault("manual_name", record_by_id.get("name"))
                else:
                    lang = get_preferred_language()
                    warning = get_message("manual_employee_not_found", lang)
                    print(f"[Flow] Employee lookup by ID returned no record: {employee_id}")
                    return False, warning, FlowState.MANUAL_VERIFICATION
            except Exception as lookup_error:
                print(f"[Flow] Employee lookup by ID failed: {lookup_error}")
                lang = get_preferred_language()
                return False, get_message("manual_employee_lookup_failed", lang, error=lookup_error), FlowState.MANUAL_VERIFICATION

        if resolved_email:
            session.user_data["manual_email"] = resolved_email
        if name:
            session.user_data["manual_name"] = name
        if employee_id:
            session.user_data["manual_employee_id"] = employee_id

        try:
            from tools.employee_verification import get_employee_details  # async function
            import asyncio
        except Exception as e:
            lang = get_preferred_language()
            return False, get_message("manual_preparation_error", lang, error=e), FlowState.MANUAL_VERIFICATION

        if otp:
            try:
                from tools.employee_verification import verify_otp_sync
                msg = verify_otp_sync(resolved_email, otp, employee_id)
            except ImportError:
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    msg = asyncio.run(get_employee_details(None, resolved_email, name, employee_id, otp))
                except Exception as async_error:
                    print(f"[Flow] Async OTP verification error: {async_error}")
                    lang = get_preferred_language()
                    return False, get_message("manual_internal_error_retry", lang), FlowState.MANUAL_VERIFICATION
            except Exception as e:
                print(f"[Flow] OTP verification error: {e}")
                return False, "I encountered an internal error during the verification process. Could you please provide the OTP again?", FlowState.MANUAL_VERIFICATION

            success = ("✅" in msg) and ("OTP verified" in msg or "Welcome" in msg)
            if success:
                session.user_data["verification_method"] = "manual_with_otp"
                session.is_verified = True
                session.current_state = FlowState.EMPLOYEE_VERIFIED
                from agent_state import set_user_verified
                verified_name = session.user_data.get("manual_name") or name
                verified_id = session.user_data.get("manual_employee_id") or employee_id
                set_user_verified(verified_name, verified_id)
                self.save_sessions()
                lang = get_preferred_language()
                credentials_prompt = get_message("manual_credentials_verified", lang, name=verified_name or "")
                combined_message = msg.strip() if msg else ""
                if combined_message:
                    combined_message = f"{combined_message}\n\n{credentials_prompt}"
                else:
                    combined_message = credentials_prompt
                return True, combined_message, FlowState.EMPLOYEE_VERIFIED
            else:
                lang = get_preferred_language()
                return False, (msg or get_message("manual_otp_failed", lang)), FlowState.MANUAL_VERIFICATION

        # No OTP yet; send one
        try:
            from tools.employee_verification import send_otp_sync
            msg, record = send_otp_sync(resolved_email, employee_id)
        except ImportError:
            try:
                import nest_asyncio
                nest_asyncio.apply()
                msg = asyncio.run(get_employee_details(None, resolved_email, name, employee_id, None))
            except Exception as async_error:
                print(f"[Flow] Async OTP sending error: {async_error}")
                lang = get_preferred_language()
                return False, get_message("manual_otp_send_failed", lang, error=async_error), FlowState.MANUAL_VERIFICATION
        except Exception as e:
            print(f"[Flow] OTP sending error: {e}")
            lang = get_preferred_language()
            return False, get_message("manual_otp_send_failed", lang, error=e), FlowState.MANUAL_VERIFICATION

        if record:
            if record.get("name"):
                session.user_data["manual_name"] = record.get("name")
            if record.get("employee_id"):
                session.user_data["manual_employee_id"] = record.get("employee_id")
            if record.get("email"):
                session.user_data["manual_email"] = record.get("email")

        lang = get_preferred_language()
        return False, (msg or get_message("manual_otp_sent", lang)), FlowState.MANUAL_VERIFICATION
    
    def process_face_registration_choice(self, register_face: bool) -> Tuple[bool, str, FlowState]:
        """Process face registration after manual verification"""
        session = self.get_current_session()
        if not session or not session.is_verified:
            lang = get_preferred_language()
            return False, get_message("manual_not_verified", lang), FlowState.IDLE
        
        if register_face:
            session.current_state = FlowState.FACE_REGISTRATION
            # Signal frontend to capture a photo and call the registration endpoint
            try:
                from flow_signal import post_signal
                post_signal("start_face_registration", {
                    "message": get_message("face_registration_ready", get_preferred_language()),
                    "next_endpoint": "/flow/register_face"
                })
            except Exception as _e:
                print(f"Warning: could not post start_face_registration signal: {_e}")
            self.save_sessions()
            lang = get_preferred_language()
            return True, get_message("face_registration_ready", lang), FlowState.FACE_REGISTRATION
        else:
            # Skip face registration and go directly to conversation mode
            session.current_state = FlowState.EMPLOYEE_VERIFIED
            self.save_sessions()
            lang = get_preferred_language()
            return True, get_message("face_registration_skip_ack", lang), FlowState.EMPLOYEE_VERIFIED
    
    def process_face_registration_completion(self, success: bool, message: str = None) -> Tuple[bool, str, FlowState]:
        """Process face registration completion - matches flowchart"""
        session = self.get_current_session()
        if not session or not session.is_verified:
            return False, "Invalid session or not verified", FlowState.IDLE
        
        if success:
            # Face registration successful - transition to final state
            session.current_state = FlowState.EMPLOYEE_VERIFIED
            session.user_data["face_registered"] = True
            self.save_sessions()
            lang = get_preferred_language()
            return True, get_message("face_registration_success", lang), FlowState.EMPLOYEE_VERIFIED
        else:
            # Face registration failed - still give access but without face registration
            session.current_state = FlowState.EMPLOYEE_VERIFIED
            self.save_sessions()
            lang = get_preferred_language()
            failure_detail = message or 'Unknown error'
            return True, f"{get_message('face_registration_skip_ack', lang)} ({failure_detail})", FlowState.EMPLOYEE_VERIFIED
    
    async def process_visitor_info(self, name: str, phone: str, purpose: str, host_employee: str) -> Tuple[bool, str, FlowState]:
        """Process visitor information collection"""
        try:
            print(f"[Flow] process_visitor_info starting with: name='{name}', phone='{phone}', purpose='{purpose}', host='{host_employee}'")

            session = self.get_current_session()
            if not session or session.user_type != UserType.VISITOR:
                print(f"[Flow] ERROR: Invalid session or user type. Session: {session}, UserType: {session.user_type if session else 'None'}")
                return False, "Invalid session or user type", FlowState.IDLE

            lang = get_preferred_language()
            updated = False

            name_candidate = (name or "").strip()
            if name_candidate and session.user_data.get("visitor_name") != name_candidate:
                session.user_data["visitor_name"] = name_candidate
                updated = True
            trimmed_name = (session.user_data.get("visitor_name") or "").strip()

            phone_candidate = (phone or "").strip()
            if phone_candidate and session.user_data.get("visitor_phone") != phone_candidate:
                session.user_data["visitor_phone"] = phone_candidate
                updated = True
            trimmed_phone = (session.user_data.get("visitor_phone") or "").strip()

            purpose_candidate = (purpose or "").strip()
            if purpose_candidate and session.user_data.get("visitor_purpose") != purpose_candidate:
                session.user_data["visitor_purpose"] = purpose_candidate
                updated = True
            trimmed_purpose = (session.user_data.get("visitor_purpose") or "").strip()

            host_candidate = (host_employee or "").strip()
            if host_candidate and session.user_data.get("host_employee") != host_candidate:
                session.user_data["host_employee"] = host_candidate
                updated = True
            trimmed_host = (session.user_data.get("host_employee") or "").strip()

            if not trimmed_name:
                if updated:
                    self.save_sessions()
                return False, get_message("visitor_need_name", lang), FlowState.VISITOR_INFO_COLLECTION
            if not trimmed_phone:
                if updated:
                    self.save_sessions()
                return False, get_message("visitor_need_phone", lang), FlowState.VISITOR_INFO_COLLECTION
            if not trimmed_purpose:
                if updated:
                    self.save_sessions()
                return False, get_message("visitor_need_purpose", lang), FlowState.VISITOR_INFO_COLLECTION
            if not trimmed_host:
                if updated:
                    self.save_sessions()
                return False, get_message("visitor_need_host", lang), FlowState.VISITOR_INFO_COLLECTION

            if updated:
                self.save_sessions()

            session.user_data.update({
                "visitor_name": trimmed_name,
                "visitor_phone": trimmed_phone,
                "visitor_purpose": trimmed_purpose,
                "host_employee": trimmed_host
            })

            if not session.user_data.get("visitor_logged"):
                try:
                    from tools.visitor_management import log_and_notify_visitor

                    log_message = await log_and_notify_visitor(
                        None,
                        trimmed_name,
                        trimmed_phone,
                        trimmed_purpose,
                        trimmed_host,
                        False,
                        None,
                    )
                    session.user_data["visitor_logged"] = True
                    session.user_data["visitor_log_result"] = log_message
                    print(f"[Flow] Visitor log persisted: {log_message}")
                except Exception as log_error:
                    session.user_data["visitor_log_error"] = str(log_error)
                    print(f"[Flow] ERROR logging visitor: {log_error}")
                finally:
                    self.save_sessions()

            session.current_state = FlowState.HOST_NOTIFICATION
            session.last_activity = time.time()
            self.save_sessions()
            print(f"[Flow] Visitor info received: name='{trimmed_name}', phone='{trimmed_phone}', purpose='{trimmed_purpose}', host='{trimmed_host}'")

            wait_message = get_message("flow_host_notification_prompt", lang)
            return True, wait_message, FlowState.HOST_NOTIFICATION

        except Exception as e:
            print(f"[Flow] CRITICAL ERROR in process_visitor_info: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error processing visitor information: {str(e)}", FlowState.IDLE
    
    def process_visitor_face_capture(self, captured: bool = True) -> Tuple[bool, str, FlowState]:
        """Deprecated: Visitor photo capture no longer required. Provide wait message."""
        session = self.get_current_session()
        lang = get_preferred_language()
        if session and session.user_type == UserType.VISITOR:
            session.current_state = FlowState.HOST_NOTIFICATION
            session.last_activity = time.time()
            self.save_sessions()
        wait_message = get_message("flow_host_notification_prompt", lang)
        return True, wait_message, FlowState.HOST_NOTIFICATION

    def check_tool_access(self, tool_name: str) -> Tuple[bool, str]:
        session = self.get_current_session()
        if not session or not session.is_verified:
            if session and session.user_type == UserType.VISITOR:
                return False, "Visitors have limited access. Your host will assist you with any information needed."
            return False, "Please verify your identity first. Say 'Hey Clara' to start the verification process."

        restricted_tools = ['send_email', 'get_employee_details', 'company_info']

        if tool_name in restricted_tools and session.user_type != UserType.EMPLOYEE:
            return False, "This tool requires employee access."

        return True, f"Access granted for {tool_name}. How can I help you?"

    def end_session(self) -> str:
        """End the current session"""
        session = self.get_current_session()
        message = "Thank you! Session completed. Say 'Hey Clara' if you need more assistance."

        if session:
            session.current_state = FlowState.FLOW_END
            session.last_activity = time.time()
            # Remove the session so a fresh call can start immediately
            self.sessions.pop(session.session_id, None)
            self.current_session_id = None
            self.save_sessions()

        return message
    
    def cleanup_old_sessions(self, max_age_hours: int = 2):
        """Clean up old sessions"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        to_remove = []
        for session_id, session in self.sessions.items():
            if (current_time - session.last_activity) > max_age_seconds:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]
        
        if self.current_session_id in to_remove:
            self.current_session_id = None
        
        self.save_sessions()
    
    def save_sessions(self):
        """Save sessions to file"""
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                sessions_data[session_id] = {
                    "session_id": session.session_id,
                    "current_state": session.current_state.value,
                    "user_type": session.user_type.value,
                    "start_time": session.start_time,
                    "last_activity": session.last_activity,
                    "verification_attempts": session.verification_attempts,
                    "user_data": session.user_data,
                    "is_verified": session.is_verified,
                    "verification_method": session.verification_method
                }
            
            flow_data = {
                "sessions": sessions_data,
                "current_session_id": self.current_session_id,
                "last_updated": time.time()
            }
            
            from pathlib import Path
            flow_file = Path(__file__).parent.parent / "data" / "flow_sessions.json"
            flow_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(flow_file, 'w') as f:
                json.dump(flow_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving flow sessions: {e}")
    
    def load_sessions(self):
        """Load sessions from file"""
        try:
            from pathlib import Path
            flow_file = Path(__file__).parent.parent / "data" / "flow_sessions.json"
            
            if flow_file.exists():
                with open(flow_file, 'r') as f:
                    flow_data = json.load(f)
                
                sessions_data = flow_data.get("sessions", {})
                for session_id, session_data in sessions_data.items():
                    session = FlowSession(
                        session_id=session_data["session_id"],
                        current_state=FlowState(session_data["current_state"]),
                        user_type=UserType(session_data["user_type"]),
                        start_time=session_data["start_time"],
                        last_activity=session_data["last_activity"],
                        verification_attempts=session_data["verification_attempts"],
                        user_data=session_data["user_data"],
                        is_verified=session_data["is_verified"],
                        verification_method=session_data.get("verification_method")
                    )
                    self.sessions[session_id] = session
                
                self.current_session_id = flow_data.get("current_session_id")
                self.cleanup_old_sessions()
                
        except Exception as e:
            print(f"Error loading flow sessions: {e}")
    
    def get_flow_status(self) -> Dict[str, Any]:
        """Get current flow status for debugging"""
        session = self.get_current_session()
        if not session:
            return {"status": "no_active_session"}
        
        return {
            "session_id": session.session_id,
            "current_state": session.current_state.value,
            "user_type": session.user_type.value,
            "is_verified": session.is_verified,
            "verification_method": session.verification_method,
            "user_data_keys": list(session.user_data.keys()),
            "last_activity": datetime.fromtimestamp(session.last_activity).strftime("%Y-%m-%d %H:%M:%S")
        }


# Global flow manager instance
flow_manager = VirtualReceptionistFlow()