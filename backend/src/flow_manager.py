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


class FlowState(Enum):
    """Flow states matching the flowchart"""
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
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
        session_id = self.create_session()
        session = self.get_current_session()
        session.current_state = FlowState.USER_CLASSIFICATION
        
        self.save_sessions()
        return True, "Hello, my name is clara, the receptionist at an Info Services, How may I help you today?"
        
    
    def process_user_classification(self, user_input: str) -> Tuple[bool, str, FlowState]:
        """Process user type classification"""
        session = self.get_current_session()
        if not session:
            return False, "No active session. Please say 'Hey Clara' to start.", FlowState.IDLE
        
        user_input_lower = user_input.lower().strip()
        
        if any(word in user_input_lower for word in ['employee', 'staff', 'worker', 'work here']):
            session.user_type = UserType.EMPLOYEE
            session.current_state = FlowState.FACE_RECOGNITION
            session.last_activity = time.time()
            
            # Signal frontend to start face capture - ONLY NOW after employee classification
            from flow_signal import post_signal
            post_signal("start_face_capture", {
                "message": "Employee verified - starting face recognition",
                "next_endpoint": "/flow/face_recognition"
            })
            
            self.save_sessions()
            return True, "Great! Please show your face to the camera for recognition.", FlowState.FACE_RECOGNITION
            
        elif any(word in user_input_lower for word in ['visitor', 'guest', 'visiting', 'meeting']):
            session.user_type = UserType.VISITOR
            session.current_state = FlowState.VISITOR_INFO_COLLECTION
            session.last_activity = time.time()
            self.save_sessions()
            return True, "Welcome! Please provide your name, phone number, purpose of visit, and who you're meeting.", FlowState.VISITOR_INFO_COLLECTION
        
        # If unclear, ask for clarification
        return False, "I didn't catch that. Are you an Employee or a Visitor?", FlowState.USER_CLASSIFICATION
    
    def process_face_recognition_result(self, face_result: Dict[str, Any]) -> Tuple[bool, str, FlowState]:
        """Process face recognition results for employees"""
        session = self.get_current_session()
        if not session or session.user_type != UserType.EMPLOYEE:
            return False, "Invalid session or user type", FlowState.IDLE
        
        if face_result.get("status") == "success":
            # Face match found
            emp_name = face_result.get("name")
            emp_id = face_result.get("employeeId")
            
            session.user_data.update({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "verification_method": "face_recognition"
            })
            session.is_verified = True
            session.current_state = FlowState.EMPLOYEE_VERIFIED
            
            # Update global verification state
            from agent_state import set_user_verified
            set_user_verified(emp_name, emp_id)
            
            self.save_sessions()
            return True, f"Face registered in system! Welcome {emp_name}. You now have full access to all tools.", FlowState.EMPLOYEE_VERIFIED
        
        else:
            # Face not matched - proceed to manual verification
            session.current_state = FlowState.MANUAL_VERIFICATION
            session.verification_attempts += 1
            self.save_sessions()
            return False, "Face not recognized. Please provide your name and employee ID for manual verification.", FlowState.MANUAL_VERIFICATION
    
    def process_manual_verification_step(self, name: str = None, employee_id: str = None, otp: str = None) -> Tuple[bool, str, FlowState]:
        """Process manual employee verification steps"""
        session = self.get_current_session()
        if not session:
            return False, "No active session", FlowState.IDLE
        
        if not name or not employee_id:
            return False, "Please provide both your name and employee ID.", FlowState.MANUAL_VERIFICATION
        
        # Store the credentials for potential face registration
        session.user_data.update({
            "manual_name": name,
            "manual_employee_id": employee_id
        })
        
        if otp:
            # OTP verification step
            session.user_data["verification_method"] = "manual_with_otp"
            session.is_verified = True
            session.current_state = FlowState.CREDENTIAL_CHECK
            
            from agent_state import set_user_verified
            set_user_verified(name, employee_id)
            
            self.save_sessions()
            return True, f"Credentials verified! Welcome {name}. Would you like to register your face for faster access next time? (Yes/No)", FlowState.CREDENTIAL_CHECK
        else:
            # Initial verification - need OTP
            return False, "OTP has been sent to your registered email. Please provide the OTP to complete verification.", FlowState.MANUAL_VERIFICATION
    
    def process_face_registration_choice(self, register_face: bool) -> Tuple[bool, str, FlowState]:
        """Process face registration after manual verification"""
        session = self.get_current_session()
        if not session or not session.is_verified:
            return False, "Invalid session or not verified", FlowState.IDLE
        
        if register_face:
            session.current_state = FlowState.FACE_REGISTRATION
            # Signal frontend to capture a photo and call the registration endpoint
            try:
                from flow_signal import post_signal
                post_signal("start_face_registration", {
                    "message": "Please look at the camera to register your face.",
                    "next_endpoint": "/flow/register_face"
                })
            except Exception as _e:
                print(f"Warning: could not post start_face_registration signal: {_e}")
            self.save_sessions()
            return True, "Please look at the camera to register your face for future quick access.", FlowState.FACE_REGISTRATION
        else:
            session.current_state = FlowState.EMPLOYEE_VERIFIED
            self.save_sessions()
            return True, "No problem! You now have full access to all tools.", FlowState.EMPLOYEE_VERIFIED
    
    def process_visitor_info(self, name: str, phone: str, purpose: str, host_employee: str) -> Tuple[bool, str, FlowState]:
        """Process visitor information collection"""
        session = self.get_current_session()
        if not session or session.user_type != UserType.VISITOR:
            return False, "Invalid session or user type", FlowState.IDLE
        
        session.user_data.update({
            "visitor_name": name,
            "visitor_phone": phone,
            "visitor_purpose": purpose,
            "host_employee": host_employee
        })
        session.current_state = FlowState.VISITOR_FACE_CAPTURE
        self.save_sessions()
        
        return True, "Thank you! Please look at the camera so we can capture your photo for our visitor log.", FlowState.VISITOR_FACE_CAPTURE
    
    def process_visitor_face_capture(self, captured: bool = True) -> Tuple[bool, str, FlowState]:
        """Process visitor face capture"""
        session = self.get_current_session()
        if not session or session.user_type != UserType.VISITOR:
            return False, "Invalid session or user type", FlowState.IDLE
        
        if captured:
            session.user_data["face_captured"] = True
            session.user_data["face_capture_time"] = datetime.now().isoformat()
            session.current_state = FlowState.HOST_NOTIFICATION
            
            visitor_data = session.user_data
            host_name = visitor_data.get('host_employee', 'Unknown')
            
            session.current_state = FlowState.FLOW_END
            self.save_sessions()
            
            return True, f"Photo captured! {host_name} has been notified. Please wait at reception.", FlowState.FLOW_END
        else:
            return False, "Photo capture failed. Please try again.", FlowState.VISITOR_FACE_CAPTURE
    
    def process_tool_request(self, tool_name: str) -> Tuple[bool, str]:
        """Process tool access requests"""
        session = self.get_current_session()
        
        # Check if user has access
        if not session or not session.is_verified:
            if session and session.user_type == UserType.VISITOR:
                return False, "Visitors have limited access. Your host will assist you with any information needed."
            else:
                return False, "Please verify your identity first. Say 'Hey Clara' to start the verification process."
        
        # Employee verified - grant access based on tool type
        restricted_tools = ['send_email', 'get_employee_details', 'company_info']
        
        if tool_name in restricted_tools and session.user_type != UserType.EMPLOYEE:
            return False, "This tool requires employee access."
        
        return True, f"Access granted for {tool_name}. How can I help you?"
    
    def end_session(self) -> str:
        """End the current session"""
        session = self.get_current_session()
        if session:
            session.current_state = FlowState.FLOW_END
            self.save_sessions()
        
        return "Thank you! Session completed. Say 'Hey Clara' if you need more assistance."
    
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