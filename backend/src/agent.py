import json
import logging
import time
import calendar
import re
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.agents.llm.realtime import RealtimeError
from livekit.plugins import google

from agent_state import get_preferred_language, process_input
from flow_manager import FlowState, UserType, flow_manager
from language_utils import get_message
from mem0_client import add_employee_memory, search_employee_memories, get_all_employee_memories
from prompts import AGENT_INSTRUCTION
from tools import (
    check_face_registration_status,
    company_info,
    face_verify,
    get_employee_details,
    employee_details,
    get_visitor_log,
    get_weather,
    listen_for_commands,
    register_employee_face,
    search_web,
    send_email,
    memory_add,
    memory_get_all,
    memory_update,
    memory_delete,
    memory_recall,
    memory_list_reminders,
)


def _sanitize_response_text(text: str) -> str:
    if not text:
        return text

    lang = get_preferred_language()
    lowered = text.lower()
    replacements = (
        ("i am sorry, i am not able to understand", "language_support_affirm"),
        ("i only speak english", "language_support_affirm"),
        ("could you please speak in english", "language_support_affirm"),
        ("i am currently limited to english", "language_support_affirm"),
        ("prefer to speak in tamil", "language_support_affirm"),
        ("prefer to speak in telugu", "language_support_affirm"),
        ("prefer to speak in hindi", "language_support_affirm"),
        ("prefer to speak in english", "language_support_affirm"),
        ("i understand you prefer to speak", "language_support_affirm"),
        ("what do you want to search for", "search_prompt"),
        ("what would you like me to search for", "search_prompt"),
    )
    for phrase, message_key in replacements:
        if phrase in lowered:
            return get_message(message_key, lang)
    if "i am sorry" in lowered and (
        "don't support" in lowered
        or "do not support" in lowered
        or "don't speak" in lowered
        or "do not speak" in lowered
        or "cannot speak" in lowered
        or "can't speak" in lowered
    ):
        return get_message("language_support_affirm", lang)
    return text


def _get_state_fallback(session, lang: str, include_default: bool = True) -> str | None:
    fallback_by_state = {
        FlowState.USER_CLASSIFICATION: get_message("wake_prompt", lang),
        FlowState.FACE_RECOGNITION: get_message("flow_face_recognition_prompt", lang),
        FlowState.MANUAL_VERIFICATION: get_message("flow_manual_verification_prompt", lang),
        FlowState.CREDENTIAL_CHECK: get_message("flow_credential_check_prompt", lang),
        FlowState.FACE_REGISTRATION: get_message("flow_face_registration_prompt", lang),
        FlowState.EMPLOYEE_VERIFIED: get_message("flow_employee_verified_prompt", lang),
        FlowState.VISITOR_INFO_COLLECTION: get_message("flow_visitor_info_prompt", lang),
        FlowState.VISITOR_FACE_CAPTURE: get_message("flow_visitor_face_capture_prompt", lang),
        FlowState.HOST_NOTIFICATION: get_message("flow_host_notification_prompt", lang),
        FlowState.FLOW_END: get_message("flow_end_prompt", lang),
    }
    if session and session.current_state in fallback_by_state:
        fallback = fallback_by_state[session.current_state]
        if fallback:
            return _sanitize_response_text(fallback)
    if include_default:
        return get_message("language_support_affirm", lang)
    return None


# Load environment variables
if load_dotenv:
    load_dotenv()

# Set logging to INFO to reduce noise
logging.basicConfig(level=logging.INFO)

# -------------------------
# Flow Management Tools
# -------------------------
@function_tool
async def start_reception_flow():
    """Start the reception flow - used when wake word is detected"""
    success, message = flow_manager.process_wake_word_detected()
    return message
 
@function_tool
async def classify_user_type(user_input: str):
    """Classify user as employee or visitor based on their input"""
    try:
        import os
        import requests

        backend_url = os.getenv("BACKEND_URL", "http://clara-alb-dev-926087638.us-east-1.elb.amazonaws.com")
        print(f"🌐 [Agent] classify_user_type -> {backend_url}/flow/classify_user")
        response = requests.post(
            f"{backend_url}/flow/classify_user",
            json={"user_input": user_input},
            timeout=5,
        )

        if response.ok:
            data = response.json()
            message = data.get("response") or data.get("message") or ""
            success = data.get("success", False)
            next_state = data.get("next_state")
            print(f"✅ [Agent] classify_user_type success={success}, next_state={next_state}")
            if success:
                # Backend is authoritative for posting signals; just return the message
                return message or "Classification updated."
            print(f"❌ [Agent] Classification failed via API: {message}")
            return message or "I'm still figuring out if you're an employee or a visitor."

        print(f"⚠️ [Agent] classify_user_type HTTP {response.status_code}: {response.text}")
    except Exception as exc:
        print(f"⚠️ [Agent] classify_user_type error: {exc}")

    return "I'm having trouble classifying right now. Could you repeat that?"
 
@function_tool
async def process_face_recognition(face_result_status: str, employee_name: str = None, employee_id: str = None):
    """Process face recognition results"""
    try:
        # If no specific results provided, this suggests we should tell the user to use face recognition
        if not face_result_status or face_result_status == "pending":
            return "Please tap the Employee Mode button to proceed. I'll start your verification automatically."
       
        # If face recognition succeeded but no employee data provided, try to reuse active session (never cached state)
        if face_result_status == "success" and not employee_name and not employee_id:
            session = flow_manager.get_current_session()
            if session and session.user_data:
                employee_name = session.user_data.get("employee_name")
                employee_id = session.user_data.get("employee_id")
                print(f"[DEBUG] Retrieved from session: name={employee_name}, id={employee_id}")
        
        face_result = {
            "status": face_result_status,
            "name": employee_name,
            "employeeId": employee_id
        }
        success, message, next_state = flow_manager.process_face_recognition_result(face_result)
        return message
    except Exception as e:
        print(f"[ERROR] process_face_recognition: {e}")
        return "I'm having trouble with face recognition. Please try manual verification instead."
 
@function_tool
async def trigger_face_recognition():
    """Tell the user to use their camera for face recognition and trigger frontend capture"""
    try:
        session = flow_manager.get_current_session()
        if not session:
            return "Let's start by waking up Clara with 'Hey Clara' and telling me if you're an employee or visitor."

        if session.is_verified:
            return "You're already verified. How else may I assist you today?"

        if session.user_type != UserType.EMPLOYEE:
            return "Before we scan, please let me know if you're an employee or a visitor."

        if session.current_state != FlowState.FACE_RECOGNITION:
            return "I need to confirm you're an employee first. Please say something like 'I'm an employee'."

        session.last_activity = time.time()
        flow_manager.save_sessions()
    except Exception as exc:
        print(f"[WARN] trigger_face_recognition state validation failed: {exc}")
        return "Let's first confirm whether you're an employee or visitor before using face recognition."

    try:
        from flow_signal import post_signal

        post_signal("start_face_capture", {
            "message": "Please tap the Employee Mode button to proceed.",
            "next_endpoint": "/flow/face_recognition",
        })
    except Exception as exc:
        print(f"[WARN] trigger_face_recognition could not emit signal: {exc}")
        return "I'm having trouble starting the face scan. Let's try again after confirming you're an employee."

    return "Please tap the Employee Mode button to proceed. I'll verify your identity automatically once you enable it."
 
@function_tool()
async def verify_employee_credentials(
    context: RunContext,
    employee_id: str,
    email: str | None = None,
    otp: str | None = None,
    name: str | None = None,
):
    """Process manual employee verification using company email or employee ID with OTP."""
    success, message, next_state = flow_manager.process_manual_verification_step(
        email=email,
        otp=otp,
        name=name,
        employee_id=employee_id,
    )
    return message
 
@function_tool
async def handle_face_registration_choice(register_face: bool):
    """Handle employee choice for face registration"""
    success, message, next_state = flow_manager.process_face_registration_choice(register_face)
    return message

@function_tool
async def complete_face_registration(success: bool, message: str = None):
    """Complete face registration process after photo capture"""
    success_result, response_message, next_state = flow_manager.process_face_registration_completion(success, message)
    return response_message
 
@function_tool
async def collect_visitor_info(name: str, phone: str, purpose: str, host_employee: str):
    """Collect visitor information"""
    try:
        print(f"[Tool] collect_visitor_info called with: name='{name}', phone='{phone}', purpose='{purpose}', host='{host_employee}'")
        
        # Ensure session is properly set up for visitor
        session = flow_manager.get_current_session()
        if not session:
            print("[Tool] No session found, creating new session")
            flow_manager.create_session()
            session = flow_manager.get_current_session()
        
        # Force set user type to VISITOR if not already set
        if session.user_type != UserType.VISITOR:
            print(f"[Tool] Fixing user type from {session.user_type} to VISITOR")
            session.user_type = UserType.VISITOR
            session.current_state = FlowState.VISITOR_INFO_COLLECTION
            flow_manager.save_sessions()
        
        success, message, next_state = await flow_manager.process_visitor_info(name, phone, purpose, host_employee)
        print(f"[Tool] collect_visitor_info result: success={success}, message='{message}', state={next_state}")
        return message
    except Exception as e:
        error_msg = f"Error collecting visitor info: {str(e)}"
        print(f"[Tool] collect_visitor_info ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        return f"I encountered an error while processing your information: {error_msg}. Please try again."
 
@function_tool
async def flow_capture_visitor_photo(captured: bool = True):
    """Process visitor photo capture within the flow manager"""
    success, message, next_state = flow_manager.process_visitor_face_capture(captured)
    return message
 
@function_tool
async def check_flow_status():
    """Get current flow status for debugging"""
    status = flow_manager.get_flow_status()
    return f"Flow Status: {status}"
 
@function_tool
async def end_current_session():
    """End the current session"""
    message = flow_manager.end_session()
    return message
 
# -------------------------
# Enhanced Verification Status Tool
# -------------------------
@function_tool
async def check_user_verification():
    """Check if the current user is verified and get their details"""
    from agent_state import load_state_from_file, is_verified, verified_user_name, verified_user_id
   
    # Load the latest state from file (shared between processes)
    load_state_from_file()
   
    # Also check flow manager session
    session = flow_manager.get_current_session()
   
    if is_verified or (session and session.is_verified):
        user_name = verified_user_name or (session.user_data.get('employee_name') if session else 'Unknown')
        user_id = verified_user_id or (session.user_data.get('employee_id') if session else 'N/A')
        return f"User is verified as {user_name} (ID: {user_id}). Full access granted."
    else:
        if session and session.user_type == UserType.VISITOR:
            return "Current user is a visitor. Limited access granted. Host will assist with sensitive information."
        else:
            return "User is not verified. Please say 'Hey Clara' to start the verification process."
 
@function_tool
async def check_tool_access(tool_name: str):
    """Check if current user has access to a specific tool"""
    has_access, message = flow_manager.check_tool_access(tool_name)
    return message if not has_access else f"Access granted for {tool_name}"
 
@function_tool
async def cleanup_old_sessions():
    """Clean up old expired sessions"""
    flow_manager.cleanup_old_sessions()
    return "✅ Session cleanup completed"
 
@function_tool  
async def get_flow_help():
    """Get help about the current flow state and available actions"""
    session = flow_manager.get_current_session()
    if not session:
        return "No active session. Say 'Hey Clara' to start the verification process."
   
    state = session.current_state
    user_type = session.user_type
   
    help_messages = {
        FlowState.IDLE: "Say 'Hey Clara' to wake me up and start the process.",
        FlowState.USER_CLASSIFICATION: "Please tell me if you are an Employee or a Visitor.",
        FlowState.FACE_RECOGNITION: "Please tap the Employee Mode button to continue with verification.",
        FlowState.MANUAL_VERIFICATION: "Please provide your name and employee ID for verification.",
        FlowState.CREDENTIAL_CHECK: "Credentials verified! You're all set to continue.",
        FlowState.FACE_REGISTRATION: "Please look at the camera to register your face.",
        FlowState.EMPLOYEE_VERIFIED: "You're verified! You can now access all tools and information.",
        FlowState.VISITOR_INFO_COLLECTION: "Please provide your name, phone, purpose of visit, and who you're meeting.",
        FlowState.VISITOR_FACE_CAPTURE: "Please look at the camera for a visitor photo.",
        FlowState.HOST_NOTIFICATION: "Your host is being notified. Please wait at reception.",
        FlowState.FLOW_END: "Session complete. Say 'Hey Clara' if you need more assistance."
    }
   
    help_text = help_messages.get(state, "Unknown state")
    return f"Current State: {state.value}\nUser Type: {user_type.value}\nNext Action: {help_text}"
 
@function_tool
async def sync_verification_status():
    """Synchronize agent verification state with flow manager"""
    session = flow_manager.get_current_session()
   
    if session and session.is_verified:
        # Sync flow manager verified state to agent state
        employee_name = session.user_data.get('employee_name')
        employee_id = session.user_data.get('employee_id')
       
        if employee_name:
            from agent_state import set_user_verified
            set_user_verified(employee_name, employee_id)
            return f"✅ Verification synchronized. Welcome {employee_name}! You have full access."
   
    return "No verified user found in current session."

@function_tool
async def get_company_information(query: str = "general"):
    """
    Get comprehensive company information from our database.
    Use this for any questions about the company, services, or general information.
    
    Args:
        query: The specific information requested (e.g., 'services', 'contact', 'about', 'location')
    """
    try:
        # First try to get company info from PDF
        from tools.company_info import company_info
        result = await company_info(None, query)
        
        # If company info is not available, try web search as backup
        if "unable to access" in result.lower() or "technical difficulties" in result.lower():
            try:
                from tools.web_search import search_web
                search_query = f"Info Services company information {query}" if query != "general" else "Info Services company"
                web_result = await search_web(None, search_query)
                return f"I couldn't access our internal company database, but here's what I found online:\n\n{web_result}"
            except Exception:
                return (
                    "I'm currently unable to access company information right now. "
                    "Let me know if you'd like me to connect you with a human teammate or provide alternative resources."
                )
        
        return result
        
    except Exception as e:
        return (
            "I'm experiencing technical difficulties retrieving company information. "
            f"I've logged the issue and can involve a human teammate if needed. Error: {str(e)}"
        )
 
 
# -------------------------
# Mem0 helpers
# -------------------------

_TIME_RANGE_PHRASES = (
    "last week",
    "last month",
    "last weekend",
    "last monday",
    "last tuesday",
    "last wednesday",
    "last thursday",
    "last friday",
    "last saturday",
    "last sunday",
)

_DAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_MEMORY_QUERY_KEYWORDS = (
    # English
    "remember",
    "recall",
    "last time",
    "previous",
    "earlier",
    "past conversation",
    "what did we",
    "history",
    "talked about",
    "repeat again",
    "repeat",
    "last session",
    "previous session",
    "previous conversation",
    "last conversation",
    "what we discussed",
    "what we discuss",
    # Tamil
    "நினைவில் வை",  # remember
    "நினைவில் வச்சுக்கோ",
    "முந்தைய",  # previous
    "முன்னால்",
    "முந்தைய உரையாடல்",
    "என்ன பேசினோம்",
    "மீண்டும் சொல்லு",  # repeat again
    # Telugu
    "గుర్తుంచుకో",  # remember
    "గుర్తు పెట్టుకో",
    "మునుపటి",  # previous
    "ముందు",
    "మునుపటి సంభాషణ",
    "ఏం మాట్లాడాము",
    "మళ్లీ చెప్పు",  # repeat again
    # Hindi
    "याद रखो",  # remember
    "याद",
    "पहले",  # earlier/previous
    "पिछली",
    "पिछली बातचीत",
    "हमने क्या बात की",
    "दोबारा बोलो",  # repeat
    "फिर से बताओ",
    *_TIME_RANGE_PHRASES,
)

_GENERAL_RECALL_KEYWORDS = (
    # English
    "repeat again",
    "repeat",
    "what did we talk",
    "what did we discuss",
    "what we talk",
    "what we discuss",
    "what we discussed",
    "last session",
    "previous session",
    "previous conversation",
    # Tamil
    "மீண்டும் சொல்லு",
    "என்ன பேசினோம்",
    # Telugu
    "మళ్లీ చెప్పు",
    "ఏం మాట్లాడాము",
    # Hindi
    "दोबारा बोलो",
    "फिर से बताओ",
    "हमने क्या बात की",
)


def _should_query_memories(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in _MEMORY_QUERY_KEYWORDS)


def _is_general_recall_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in _GENERAL_RECALL_KEYWORDS)


def _extract_about_topic(text: str) -> str | None:
    lowered = (text or "").strip()
    import re as _re
    m = _re.search(r"about\s+(.+)", lowered, _re.IGNORECASE)
    if m:
        topic = m.group(1).strip().strip("?!.")
        return topic[:128]
    return None


def _is_generic_memory_text(s: str) -> bool:
    t = (s or "").strip().lower()
    if not t:
        return True
    prefixes = (
        "user is",
        "user has",
        "user was",
        "user likes",
        "user is searching",
        "user reports",
        "user is using",
        "user wants",
        "user asked",
        "user requested",
    )
    return t.startswith(prefixes)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _parse_time_range(text: str) -> tuple[datetime, datetime, str] | None:
    lowered = (text or "").lower()
    now = datetime.now(timezone.utc)
    today = now.date()

    def start_of_day(date_obj):
        return datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=timezone.utc)

    if "last month" in lowered:
        first_this_month = today.replace(day=1)
        last_day_prev_month = first_this_month - timedelta(days=1)
        start_date = last_day_prev_month.replace(day=1)
        start_dt = start_of_day(start_date)
        end_dt = start_of_day(first_this_month)
        return start_dt, end_dt, "from last month"

    if "last week" in lowered:
        # Previous calendar week (Monday-Sunday)
        weekday = today.weekday()
        start_date = today - timedelta(days=weekday + 7)
        start_dt = start_of_day(start_date)
        end_dt = start_of_day(start_date + timedelta(days=7))
        return start_dt, end_dt, "from last week"

    if "last weekend" in lowered:
        weekday = today.weekday()
        last_sunday = today - timedelta(days=weekday + 1)
        last_saturday = last_sunday - timedelta(days=1)
        start_dt = start_of_day(last_saturday)
        end_dt = start_of_day(last_sunday + timedelta(days=1))
        return start_dt, end_dt, "from last weekend"

    for day_name, index in _DAY_NAME_TO_INDEX.items():
        phrase = f"last {day_name}"
        if phrase in lowered:
            delta = (today.weekday() - index) % 7
            if delta == 0:
                delta = 7
            target_date = today - timedelta(days=delta)
            start_dt = start_of_day(target_date)
            end_dt = start_of_day(target_date + timedelta(days=1))
            return start_dt, end_dt, f"from last {day_name.capitalize()}"

    return None


def _filter_memories_by_time_range(results, start: datetime, end: datetime):
    filtered = []
    for entry in results:
        timestamp = None
        if isinstance(entry, dict):
            timestamp = _parse_iso_datetime(entry.get("updated_at") or entry.get("created_at"))
            if not timestamp:
                metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else None
                if metadata:
                    timestamp = _parse_iso_datetime(metadata.get("updated_at") or metadata.get("created_at") or metadata.get("timestamp"))
        if not timestamp:
            continue
        if start <= timestamp < end:
            filtered.append(entry)
    return filtered


# Triggers for storing a memory explicitly (multi-language)
_MEMORY_ADD_KEYWORDS = (
    # English
    "remember this",
    "remember",
    "make a note",
    "note this",
    "save this",
    "store this",
    "mind it",
    # Tamil
    "நினைவில் வை",
    "நினைவில் வச்சுக்கோ",
    # Telugu
    "గుర్తుంచుకో",
    "గుర్తు పెట్టుకో",
    # Hindi
    "याद रखो",
    "याद करो",
    "नोट कर लो",
)


def _should_store_memory(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in _MEMORY_ADD_KEYWORDS)


_REMINDER_QUERY_KEYWORDS = (
    "reminder",
    "remind",
    "what do i have",
    "upcoming tasks",
    "what are my reminders",
    "what's on my schedule",
)


def _should_list_reminders(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in _REMINDER_QUERY_KEYWORDS)


def _is_today_schedule_query(text: str) -> bool:
    t = (text or "").lower()
    if "today" not in t and "today's" not in t:
        return False
    keywords = (
        "call",
        "calls",
        "meeting",
        "meetings",
        "schedule",
        "reminder",
        "reminders",
        "appointments",
        "appointment",
    )
    return any(k in t for k in keywords)


def _resolve_mem0_identity(session) -> tuple[str | None, str | None, dict[str, str] | None]:
    employee_id: str | None = None
    employee_name: str | None = None

    if session and session.is_verified:
        employee_id = (
            session.user_data.get("employee_id")
            or session.user_data.get("manual_employee_id")
        )
        employee_name = (
            session.user_data.get("employee_name")
            or session.user_data.get("manual_name")
        )

    try:
        from agent_state import (
            load_state_from_file as _load_state,
            is_verified as _is_verified,
            verified_user_name as _v_name,
            verified_user_id as _v_id,
        )

        _load_state()
        if _is_verified:
            employee_id = employee_id or _v_id
            employee_name = employee_name or _v_name
    except Exception:
        pass

    if employee_id and employee_name:
        mem_user_id = f"{employee_id}:{employee_name}"
    else:
        mem_user_id = employee_id or employee_name
    mem_display_name = employee_name or employee_id
    metadata = None
    if employee_id or employee_name:
        metadata = {
            "employee_id": employee_id or "",
            "employee_name": employee_name or "",
        }
    return mem_user_id, mem_display_name, metadata


def _format_memory_item(raw_memory) -> str:
    if isinstance(raw_memory, str):
        return _enrich_memory_summary(raw_memory)
    # ... (rest of the code remains the same)
    if isinstance(raw_memory, dict):
        messages = raw_memory.get("messages")
        if isinstance(messages, list):
            segments = []
            for message in messages:
                role = message.get("role")
                content = message.get("content")
                if not content:
                    continue
                prefix = "You" if role == "user" else "Clara"
                segments.append(f"{prefix}: {content}")
            if segments:
                return " | ".join(segments)
        summary = raw_memory.get("summary")
        if isinstance(summary, str):
            return summary
        return json.dumps(raw_memory, ensure_ascii=False)
    return json.dumps(raw_memory, ensure_ascii=False)


def _summarize_memories(results, display_name: str | None, descriptor: str | None = None) -> str | None:
    display = display_name or "you"
    lines: list[str] = []
    for entry in results:
        metadata = entry.get("metadata") if isinstance(entry, dict) else None
        memory_payload = entry.get("memory") if isinstance(entry, dict) else entry
        memory_text = _format_memory_item(memory_payload)
        timestamp = entry.get("updated_at") if isinstance(entry, dict) else None
        if isinstance(metadata, dict) and metadata.get("detail"):
            memory_text = metadata.get("detail")
        if not memory_text:
            continue
        if isinstance(metadata, dict):
            mem_name = metadata.get("employee_name")
            mem_id = metadata.get("employee_id")
            name_clause = None
            if mem_name and mem_id:
                name_clause = f"{mem_name} (ID {mem_id})"
            elif mem_name:
                name_clause = mem_name
            elif mem_id:
                name_clause = f"Employee ID {mem_id}"
        else:
            name_clause = None
        if timestamp:
            lines.append(
                "- "
                + (
                    f"[{name_clause}] " if name_clause else ""
                )
                + f"{memory_text} (updated {timestamp})"
            )
        else:
            lines.append(
                "- "
                + (
                    f"[{name_clause}] " if name_clause else ""
                )
                + f"{memory_text}"
            )

    if not lines:
        return None

    return "\n".join(lines)


def _enrich_memory_summary(text: str) -> str:
    lowered = text.strip()
    if not lowered:
        return text
    patterns = (
        (r"^user is searching for (.+)$", "You researched {match}.", True),
        (r"^user is working on (.+)$", "You were working on {match}.", True),
        (r"^user has a (.+)$", "You had {match}.", True),
        (r"^user reports (.+)$", "You reported {match}.", True),
        (r"^user is using (.+)$", "You were using {match}.", True),
        (r"^user wants to (.+)$", "You wanted to {match}.", False),
        (r"^user wants (.+)$", "You wanted {match}.", False),
        (r"^user asked (.+)$", "You asked {match}.", False),
        (r"^user requested (.+)$", "You requested {match}.", False),
        (r"^user is working on a (.+)$", "You were working on a {match}.", True),
    )
    for pattern, template, capitalize in patterns:
        m = re.match(pattern, lowered, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if capitalize and val:
                val = val[0].upper() + val[1:]
            return template.format(match=val)
    return text


def _summarize_memories_to_list(results, display_name: str | None, max_items: int = 5, descriptor: str | None = None) -> str | None:
    if not results:
        return None
    lines: list[str] = []
    for i, entry in enumerate(results[:max_items], 1):
        text = entry.get("memory") if isinstance(entry, dict) else entry
        formatted = _format_memory_item(text)
        if not formatted:
            continue
        metadata = entry.get("metadata") if isinstance(entry, dict) else None
        if isinstance(metadata, dict) and metadata.get("detail"):
            formatted = metadata.get("detail")
        timestamp = None
        if isinstance(entry, dict):
            timestamp = entry.get("updated_at") or entry.get("created_at")
        ts_note = f" (updated {timestamp})" if timestamp else ""
        lines.append(f"- {formatted}{ts_note}")
    if not lines:
        return None
    return "\n".join(lines)


def _should_log_memory(session, mem_user_id: str | None) -> bool:
    if session and session.user_type == UserType.EMPLOYEE and session.is_verified:
        return True
    return bool(mem_user_id)


def _persist_employee_memory(
    mem_user_id: str,
    user_text: str,
    assistant_text: str,
    metadata: dict[str, str] | None,
) -> None:
    if not user_text or not assistant_text:
        return
    payload = [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_text},
    ]
    # Add employee name as ENTITIES for Mem0 dashboard grouping
    entities = None
    if isinstance(metadata, dict):
        emp_name = metadata.get("employee_name")
        if emp_name:
            entities = [emp_name]
    add_employee_memory(payload, user_id=mem_user_id, metadata=metadata, entities=entities)


def _get_upcoming_reminders(mem_user_id: str | None, horizon_hours: int = 24, include_overdue: bool = True) -> str | None:
    if not mem_user_id:
        return None
    try:
        items = get_all_employee_memories(mem_user_id)
    except Exception as exc:
        print(f"⚠️ Failed to fetch reminders: {exc}")
        return None

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=max(1, horizon_hours))
    reminders: list[tuple[datetime, str]] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("type") != "reminder":
            continue
        reminder_dt = _parse_iso_datetime(metadata.get("reminder_time"))
        if not reminder_dt:
            continue
        is_due = include_overdue and reminder_dt <= now
        in_window = now < reminder_dt <= horizon
        if not (is_due or in_window):
            continue
        detail = metadata.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            detail = item.get("memory") if isinstance(item.get("memory"), str) else None
        if not detail:
            detail = "You have something scheduled."
        reminders.append((reminder_dt, detail.strip()))

    if not reminders:
        return None

    reminders.sort(key=lambda x: x[0])
    lines = []
    for reminder_dt, detail in reminders[:3]:
        human_time = reminder_dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"- {human_time}: {detail}")

    if len(reminders) > 3:
        lines.append(f"- ...and {len(reminders) - 3} more")

    return "Reminder:\n" + "\n".join(lines)


# -------------------------
# Define the Assistant Agent
# -------------------------
class Assistant(Agent):
    def __init__(self):
        # Agent name for internal reference (do not assign to Agent.label which is read-only)
        self.agent_name = "clara-receptionist"
       
        # Updated instructions to include Clara's wake/sleep behavior and new flow
        clara_instructions = """
You are Clara, a WAKE WORD ACTIVATED virtual receptionist.

🎯 FACE VERIFICATION DIRECTIVE HANDLING (HIGHEST PRIORITY):
- When you receive a message containing "[[sys:face_verified]]" with a "Suggested greeting:", extract the suggested greeting text and speak it exactly as written, covering every sentence in order.
- DO NOT shorten, paraphrase, or skip any part of the suggested greeting.
- DO NOT add extra commentary or follow-up sentences after speaking the suggested greeting unless the user asks for more.
- Never announce that the session has ended unless the user explicitly asks to end it.
 
🔥 CRITICAL WAKE WORD BEHAVIOR:
- You START IN SLEEP MODE - DO NOT respond to anything except "Hey Clara"
- When you hear "Hey Clara" → IMMEDIATELY use start_reception_flow() tool
- Only after wake word detection → ask "Hello! Are you an Employee or a Visitor?"
- If user talks without saying "Hey Clara" first → IGNORE completely (return None)
 
FLOW SEQUENCE AFTER WAKE UP:
1. Wake Word: "Hey Clara" → use start_reception_flow() → ask employee/visitor question
2. Employee Classification: "I am employee" → use classify_user_type("I am employee") → automatically triggers face scan
3. Visitor Classification: "I am visitor" → use classify_user_type("I am visitor") → collect visitor info
4. Face Recognition: Automatically triggered after employee classification
5. Manual Verification: If face fails, use verify_employee_credentials()
6. Session End: Use end_current_session() when complete
 
⚠️ WAKE WORD RULES:
- NEVER respond without "Hey Clara" first
- NEVER start conversations automatically  
- NEVER skip the wake word detection step
- Always use the flow management tools in sequence
 
VERIFICATION RULES:
- Employees get full access after verification
- Visitors get limited access and host assistance
- Always verify identity before providing company information
- Use check_user_verification() to check current status

🏢 COMPANY INFORMATION HANDLING:
- When users ask about company info, services, or general questions → ALWAYS use company_info() tool first
- Common triggers: "company information", "about company", "services", "what do you do", "tell me about"
- If company_info fails or is unavailable → use search_web() as backup
- For specific searches, pass the query to company_info(query="user's question")
- Always prioritize company PDF data over web search results

📞 INFORMATION ACCESS PRIORITY:
1. First: Use company_info() tool for any company-related questions
2. Second: If company info unavailable, use search_web() tool  
3. Third: Provide helpful guidance to contact reception

👤 EMPLOYEE SELF-DETAILS (AFTER VERIFICATION):
- When an employee asks "give/provide information of me", "my details", "show my profile" → ALWAYS use employee_details() with no fields. Speak the result as friendly sentences one-by-one.
- For specific requests like "what is my role", "what's my joining date", "what is my department" → call employee_details(fields="role") or employee_details(fields="date_of_joining") or employee_details(fields="department").
- Synonyms are supported: role/designation/title/position; joining date/date of joining/DOJ; phone/mobile; manager/reporting manager.
- Keep responses concise for specific questions: answer with only the requested field (e.g., just the role or just the joining date) without prefaces.
- Do NOT say phrases like "Verified as ..." in responses.
- Do NOT read photo URLs, raw internal IDs, or GUIDs aloud. If a manager field is an ID, resolve the name instead.
- Never disclose other employees' information. Only the currently verified employee's details are allowed.
- Short help message for verified employees: "You can say: 'show my details', 'what is my role?', or 'what's my joining date?'"

STATE MANAGEMENT:
- Sleep: Only respond to "Hey Clara"
- Awake: Follow the complete flow process
- Auto-sleep after 3 minutes of inactivity
 
""" + AGENT_INSTRUCTION
       
        tool_list = [
            # Flow management tools
            start_reception_flow,
            classify_user_type,
            process_face_recognition,
            trigger_face_recognition,
            verify_employee_credentials,
            handle_face_registration_choice,
            complete_face_registration,
            collect_visitor_info,
            flow_capture_visitor_photo,
            check_flow_status,
            end_current_session,
            # Verification and access control
            check_user_verification,
            check_tool_access,
            # Flow completion and help
            cleanup_old_sessions,
            get_flow_help,
            sync_verification_status,
            # Enhanced company information tool
            get_company_information,
            # Core business tools  
            company_info,
            get_employee_details,
            employee_details,
            listen_for_commands,
            get_weather,
            search_web,
            send_email,
            # Mem0 memory tools (private per verified employee)
            memory_add,
            memory_get_all,
            memory_update,
            memory_delete,
            memory_recall,
            # log_and_notify_visitor,  # Removed - use collect_visitor_info instead
            # Face registration tools
            register_employee_face,
            check_face_registration_status,
            # Face verification tools
            face_verify,
            get_visitor_log,
        ]

        # Filter out optional tools that may not be available (e.g., when dependencies are missing)
        tool_list = [tool for tool in tool_list if tool is not None]

        super().__init__(
            instructions=clara_instructions,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.3,
            ),
            tools=tool_list,
        )
       
    async def handle_message(self, message):
        """Override message handling to implement wake/sleep and flow logic"""
        # Get the text content from the message
        text_content = getattr(message, 'text', '') or str(message)
        print(f"🎤 Received message: '{text_content}'")

        session = flow_manager.get_current_session()
        mem_user_id, mem_display_name, mem_metadata = _resolve_mem0_identity(session)

        def respond_with_memory(response_text: str):
            if response_text and mem_user_id and _should_log_memory(session, mem_user_id):
                _persist_employee_memory(mem_user_id, text_content, response_text, mem_metadata)
            return response_text

        # Check if this is a face verification directive from the frontend
        print(f"🔍 DEBUG: Checking for face verification directive in: {text_content[:100]}...")
        if "[[sys:face_verified]]" in text_content and "Suggested greeting:" in text_content:
            print(f"✅ DEBUG: Face verification directive detected!")
            # Extract employee info and suggested greeting
            import re
            emp_match = re.search(r'Employee:\s*([^(]+)(?:\((\d+)\))?', text_content)
            greeting_match = re.search(r'Suggested greeting:\s*(.+)', text_content, re.DOTALL)
            
            if emp_match and greeting_match:
                emp_name = emp_match.group(1).strip()
                emp_id = emp_match.group(2)
                suggested_greeting = greeting_match.group(1).strip()
                clean_greeting = " ".join(
                    segment
                    for segment in (
                        line.strip()
                        for line in suggested_greeting.splitlines()
                    )
                    if segment
                )
                # If the greeting forgot to include the name, inject it into a common pattern
                try:
                    if emp_name:
                        if "Hello, ." in clean_greeting:
                            clean_greeting = clean_greeting.replace("Hello, .", f"Hello, {emp_name}.")
                        elif clean_greeting.startswith("Hello, ") and (clean_greeting[7:9] in {".", "!"}):
                            # Edge case: 'Hello, !' or 'Hello, .' at start
                            clean_greeting = f"Hello, {emp_name}{clean_greeting[6:]}"
                except Exception:
                    pass
                
                # Update flow state to mark employee as verified
                print(f"🔧 DEBUG: Processing face verification for {emp_name} ({emp_id})")
                try:
                    from agent_state import set_user_verified
                    set_user_verified(emp_name, emp_id)
                    print(f"✅ DEBUG: agent_state updated for {emp_name}")

                    # Ensure a flow session exists so subsequent tools see verification immediately
                    session = flow_manager.get_current_session()
                    print(f"🔍 DEBUG: Current session exists: {session is not None}")
                    if not session:
                        try:
                            flow_manager.create_session()
                            session = flow_manager.get_current_session()
                            print(f"🆕 DEBUG: Created new session: {session is not None}")
                        except Exception as create_ex:
                            print(f"❌ DEBUG: Failed to create session: {create_ex}")
                            session = None

                    if session:
                        session.is_verified = True
                        session.user_type = UserType.EMPLOYEE
                        session.current_state = FlowState.EMPLOYEE_VERIFIED
                        session.user_data.update({
                            "employee_name": emp_name,
                            "employee_id": emp_id,
                            "verification_method": "face_recognition"
                        })
                        flow_manager.save_sessions()
                        print(f"✅ DEBUG: Flow session updated and saved for {emp_name}")
                    else:
                        print(f"❌ DEBUG: No session available to update")
                except Exception as e:
                    print(f"⚠️ Error updating flow state: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Suppress duplicate greetings within a short window
                try:
                    now = time.time()
                    if session:
                        curr_hash = str(hash(clean_greeting))
                        last_hash = session.user_data.get("last_greeting_hash")
                        last_ts = session.user_data.get("last_greeting_ts")
                        if last_hash == curr_hash and last_ts and now - float(last_ts) < 15:
                            return ""
                        session.user_data["last_greeting_hash"] = curr_hash
                        session.user_data["last_greeting_ts"] = now
                        flow_manager.save_sessions()
                except Exception:
                    pass
                
                print("✅ Face verified - Clara will speak full greeting:")
                print(f"   '{clean_greeting}'")
                try:
                    mem_user_id = None
                    if emp_id and emp_name:
                        mem_user_id = f"{emp_id}:{emp_name}"
                    else:
                        mem_user_id = emp_id or emp_name
                    reminder_digest = _get_upcoming_reminders(mem_user_id)
                except Exception as reminder_exc:
                    print(f"⚠️ Reminder digest error: {reminder_exc}")
                    reminder_digest = None

                response_text = clean_greeting
                if reminder_digest:
                    response_text = f"{clean_greeting}\n\n{reminder_digest}"

                return respond_with_memory(response_text)
            else:
                print("⚠️ Face verified but couldn't extract employee info or greeting")

        # First, see if verification has been completed out-of-band (via server endpoints)
        try:
            from agent_state import load_state_from_file as _load_state, is_verified as _is_verified, verified_user_name as _vun, verified_user_id as _vuid
            _load_state()
            if _is_verified:
                # Advance flow as if face recognition succeeded
                face_result = {"status": "success", "name": _vun, "employeeId": _vuid}
                _, message_out, _ = flow_manager.process_face_recognition_result(face_result)
                if message_out:
                    print("✅ Detected external verification; advancing flow")
                    return respond_with_memory(message_out)
        except Exception as _e:
            print(f"(non-fatal) verification sync error: {_e}")
        
        verified_session = False
        try:
            verified_session = bool(session and session.is_verified)
        except Exception:
            verified_session = False

        # Also trust the persisted agent state to avoid race conditions with session creation
        if not verified_session:
            try:
                from agent_state import load_state_from_file as _load_state, is_verified as _is_verified
                _load_state()
                if _is_verified:
                    verified_session = True
            except Exception:
                pass

        if verified_session:
            t = (text_content or "").lower()
            def _any_phrase(s: str, phrases: tuple[str, ...]) -> bool:
                return any(p in s for p in phrases)
            if _any_phrase(t, ("my details", "provide my details", "my profile", "show my details", "show my profile")):
                try:
                    out = await employee_details(None)
                    if out:
                        return respond_with_memory(out)
                except Exception:
                    pass
            intent_map = [
                (("my role", "what is my role", "designation", "title", "position"), "role"),
                (("my manager", "who is my manager", "reporting manager", "report manager", "reports to"), "manager"),
                (("my department", "what is my department", "team"), "department"),
                (("joining date", "date of joining", "doj", "my joining date"), "date_of_joining"),
                (("my phone", "my mobile", "phone number", "mobile number"), "phone"),
                (("my email", "email address", "my mail"), "email"),
                (("my location", "office location", "my office", "my site"), "location"),
            ]
            for phrases, field in intent_map:
                if _any_phrase(t, phrases):
                    try:
                        out = await employee_details(None, fields=field)
                        if out:
                            return respond_with_memory(out)
                    except Exception:
                        pass
        
        # Proactive store: if user asks to remember/save a note (multi-language)
        # Only when the text does NOT appear to be a recall request
        if mem_user_id and _should_store_memory(text_content) and not (
            _should_query_memories(text_content) or _is_general_recall_request(text_content)
        ):
            try:
                info = text_content.strip()
                payload = [
                    {"role": "user", "content": info},
                    {"role": "assistant", "content": f"Noted: {info}"},
                ]
                entities = [mem_display_name] if mem_display_name else None
                meta = dict(mem_metadata or {})
                meta.setdefault("type", "explicit_memory")
                meta["detail"] = info
                ok = add_employee_memory(
                    payload,
                    user_id=mem_user_id,
                    metadata=meta,
                    entities=entities,
                    custom_categories=[{"notes": "Personal notes"}],
                )
                if ok:
                    return respond_with_memory("✅ Saved to your private memory.")
                else:
                    return respond_with_memory("⚠️ I couldn't save that right now. Please try again later.")
            except Exception as mem_err:
                print(f"⚠️ Error saving explicit memory: {mem_err}")
                return respond_with_memory("⚠️ I couldn't save that right now. Please try again later.")

        # Fast path for today's schedule queries
        if mem_user_id and _is_today_schedule_query(text_content):
            try:
                result = await memory_recall(None, text_content, limit=5)
                if result:
                    return respond_with_memory(result)
            except Exception:
                pass

        # List reminders (general schedule queries)
        if mem_user_id and _should_list_reminders(text_content):
            try:
                out = await memory_list_reminders(None, within_hours=168, include_overdue=True)
                if out:
                    return respond_with_memory(out)
            except Exception:
                pass

        if mem_user_id and _should_query_memories(text_content):
            time_range = _parse_time_range(text_content)
            try:
                topic = _extract_about_topic(text_content)
                search_query = topic or text_content
                memory_hits = search_employee_memories(search_query, mem_user_id)
            except Exception as mem_err:
                memory_hits = []
                print(f"⚠️ Mem0 search error: {mem_err}")

            if memory_hits:
                if time_range:
                    start_dt, end_dt, descriptor = time_range
                    filtered_hits = _filter_memories_by_time_range(memory_hits, start_dt, end_dt)
                    if filtered_hits:
                        summary = _summarize_memories(filtered_hits, mem_display_name, descriptor)
                        if summary:
                            print("📚 Responding from time-filtered memories")
                            return respond_with_memory(summary)
                    else:
                        return respond_with_memory(f"I didn't record anything {descriptor}.")

                summary = _summarize_memories(memory_hits, mem_display_name)
                if summary:
                    topic = _extract_about_topic(text_content)
                    # Only consider web fallback if ALL hits are generic AND none provide metadata.detail
                    if topic:
                        try:
                            is_all_generic = True
                            has_specific_detail = False
                            for it in memory_hits:
                                md = it.get("metadata") if isinstance(it, dict) else None
                                if isinstance(md, dict):
                                    det = md.get("detail")
                                    if isinstance(det, str) and det.strip():
                                        has_specific_detail = True
                                        break
                                piece = it.get("memory") if isinstance(it, dict) else it
                                piece_text = _format_memory_item(piece)
                                if not _is_generic_memory_text(piece_text):
                                    is_all_generic = False
                                    break
                            if is_all_generic and not has_specific_detail:
                                web = await search_web(None, topic)
                                if web:
                                    return respond_with_memory(web)
                        except Exception:
                            pass
                    print("📚 Responding from stored memories")
                    return respond_with_memory(summary)
            elif _is_general_recall_request(text_content):
                try:
                    recent_items = get_all_employee_memories(mem_user_id)
                except Exception as mem_err:
                    recent_items = []
                    print(f"⚠️ Mem0 get_all error: {mem_err}")
                if recent_items:
                    descriptor = None
                    if time_range:
                        start_dt, end_dt, descriptor = time_range
                        recent_items = _filter_memories_by_time_range(recent_items, start_dt, end_dt)
                        if not recent_items:
                            return respond_with_memory(f"I didn't record anything {descriptor}.")
                    summary = _summarize_memories(recent_items, mem_display_name, descriptor)
                    if summary:
                        print("📚 Responding from full memory list (general recall)")
                        return respond_with_memory(summary)

        # Process input through our state management
        should_respond, state_response = process_input(text_content)
        print(f"🧠 State check - should_respond: {should_respond}, state_response: '{state_response}'")
        
        # If there's a state response (wake/sleep messages), handle flow
        if state_response:
            # If waking up, start the reception flow
            lang = get_preferred_language()
            wake_ack = get_message("wake_ack", lang)
            if state_response == wake_ack or "I'm awake" in state_response or "awake" in state_response.lower():
                print("🚀 Clara waking up - starting reception flow...")
                flow_success, flow_message = flow_manager.process_wake_word_detected()
                question = get_message("wake_prompt", lang)
                combined_message = f"{flow_message}\n{question}" if flow_message else question
                print(f"🔊 Combined wake message: '{combined_message}'")
                return respond_with_memory(combined_message)  # Use combined message
            return respond_with_memory(state_response)
        
        # If Clara shouldn't respond (sleeping), do not emit 'None' to UI
        if not should_respond:
            print("😴 Clara is sleeping - ignoring input")
            return ""
        
        # Check current flow status for context
        session = flow_manager.get_current_session()
        if session:
            print(f"📊 Current session state: {session.current_state.value}")
            # Update session activity
            session.last_activity = time.time()
            flow_manager.save_sessions()
            
            # Provide context-aware responses based on current flow state
            if session.current_state == FlowState.USER_CLASSIFICATION:
                print(f"🔍 In USER_CLASSIFICATION state, processing: '{text_content}'")
                
                # Call backend API for classification to ensure shared state
                try:
                    import requests
                    import os
                    # Try internal service discovery first, then fall back to ALB
                    backend_url = os.getenv("BACKEND_URL", "http://clara-alb-dev-926087638.us-east-1.elb.amazonaws.com")
                    print(f"🌐 Calling backend API at: {backend_url}/flow/classify_user")
                    classify_response = requests.post(
                        f"{backend_url}/flow/classify_user",
                        json={"user_input": text_content},
                        timeout=5
                    )
                    if classify_response.ok:
                        classify_data = classify_response.json()
                        success = classify_data.get("success", False)
                        response = classify_data.get("response", "")
                        if success:
                            print(f"✅ Classification successful via API: '{response}'")
                            return respond_with_memory(response)
                        else:
                            print(f"❌ Classification failed via API: '{response}'")
                            return respond_with_memory(response)
                    else:
                        print(f"⚠️ Backend API call failed, falling back to local flow_manager")
                except Exception as e:
                    print(f"⚠️ Error calling backend API: {e}, falling back to local flow_manager")
                
                # Fallback to local flow_manager if API call fails
                success, response, next_state = flow_manager.process_user_classification(text_content)
                if success:
                    print(f"✅ Classification successful (fallback): '{response}', next_state: {next_state.value}")
                    return respond_with_memory(response)
                else:
                    print(f"❌ Classification failed (fallback): '{response}', staying in {session.current_state.value}")
                    return respond_with_memory(response)

        # Context-aware fallback so we never send 'None' and keep a human feel
        try:
            lang = get_preferred_language()
            fb = _get_state_fallback(session, lang, include_default=False)
            if fb:
                print(f"🔄 Using context fallback for state {session.current_state.value}: '{fb}'")
                return respond_with_memory(fb)
        except Exception as _e:
            print(f"(non-fatal) fallback generation error: {_e}")

        # Normal processing for awake state
        print("🧠 Processing with LLM...")
        try:
            llm_response = await super().handle_message(message)
        except RealtimeError as err:
            print(f"❗ Realtime generation error: {err}")
            session = flow_manager.get_current_session()
            lang = get_preferred_language()
            fb = _get_state_fallback(session, lang, include_default=True)
            print("🔄 Falling back after realtime error")
            return respond_with_memory(fb)
        except Exception as err:
            print(f"❗ Unexpected LLM error: {err}")
            session = flow_manager.get_current_session()
            lang = get_preferred_language()
            fb = _get_state_fallback(session, lang, include_default=True)
            print("🔄 Falling back after unexpected LLM error")
            return respond_with_memory(fb)

        # Safety guard: never emit None/empty; use context-aware fallback instead
        if not llm_response or str(llm_response).strip().lower() in {"none", "null"}:
            try:
                session = flow_manager.get_current_session()
                lang = get_preferred_language()
                fallback = _get_state_fallback(session, lang, include_default=False)
                if fallback:
                    print(f"🔄 Using fallback for state {session.current_state.value}: '{fallback}'")
                    return fallback
            except Exception as _e:
                print(f"(non-fatal) final fallback error: {_e}")
            lang = get_preferred_language()
            return get_message("language_support_affirm", lang)

        sanitized_response = _sanitize_response_text(llm_response)
        print(f"🔊 Final LLM response: '{sanitized_response}'")
        return sanitized_response
 
# -------------------------
# Entrypoint for LiveKit worker
# -------------------------
async def entrypoint(ctx: JobContext):
    # Load shared state on startup
    from agent_state import load_state_from_file
    load_state_from_file()
   
    print(f"🤖 Clara Agent starting in room: {ctx.room.name}")
    print(f"🎯 Agent name: clara-receptionist")
    print(f"🔊 Listening for 'Hey Clara' to activate...")
   
    # # Wait for participants to join
    # await ctx.wait_for_participant()
    # print(f"👥 Participant joined room: {ctx.room.name}")
   
    # Initialize AgentSession with proper assistant
    assistant = Assistant()
    session = AgentSession(
        llm=assistant.llm,
        tts=assistant.tts,
        stt=assistant.stt,
        userdata=assistant
    )
 
    # Start the Agent session with the assistant and room
    await session.start(assistant, room=ctx.room)
   
    print(f"✅ Clara connected and ready! State: LISTENING for 'Hey Clara'")
 
 
# -------------------------
# Run the LiveKit agent
# -------------------------
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="clara-receptionist"
        )
    )