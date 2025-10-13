def _sanitize_response_text(text: str) -> str:
    if not text:
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
import os
import time
from dotenv import load_dotenv
import logging
from livekit.plugins import noise_cancellation, google
from livekit.agents import WorkerOptions, cli, JobContext
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool
from livekit.agents.llm.realtime import RealtimeError
from agent_state import (
    is_awake,
    check_auto_sleep,
    process_input,
    get_state,
    update_activity,
    get_preferred_language,
)
from tools import (
    company_info,
    get_weather,
    send_email,
    listen_for_commands,
    get_employee_details,
    register_employee_face,
    check_face_registration_status,
    capture_visitor_photo,
    get_visitor_log,
    search_web
)
from agent_state import verified_user_name, verified_user_id
from flow_manager import flow_manager, FlowState, UserType
from prompts import AGENT_INSTRUCTION
from language_utils import get_message
 
 
# Load environment variables
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
    success, message, next_state = flow_manager.process_user_classification(user_input)
   
    # If user classified as employee and moved to face recognition state, signal frontend
    if success and next_state and next_state.value == "face_recognition":
        from flow_signal import post_signal
        post_signal("start_face_capture", {
            "message": "Please show your face to the camera for employee verification",
            "next_endpoint": "/flow/face_recognition"
        })
   
    return message
 
@function_tool
async def process_face_recognition(face_result_status: str, employee_name: str = None, employee_id: str = None):
    """Process face recognition results"""
    try:
        # If no specific results provided, this suggests we should tell the user to use face recognition
        if not face_result_status or face_result_status == "pending":
            return "Please show your face to the camera for recognition. The system will automatically verify your identity."
       
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
            flow_manager.create_session()
            session = flow_manager.get_current_session()

        if session:
            if session.is_verified:
                return "You're already verified. How else may I assist you today?"
            if session.user_type == UserType.UNKNOWN:
                session.user_type = UserType.EMPLOYEE
            session.current_state = FlowState.FACE_RECOGNITION
            session.last_activity = time.time()
            flow_manager.save_sessions()
    except Exception as exc:
        print(f"[WARN] trigger_face_recognition could not sync flow state: {exc}")

    try:
        from flow_signal import post_signal

        post_signal("start_face_capture", {
            "message": "Please show your face to the camera for employee verification",
            "next_endpoint": "/flow/face_recognition",
        })
    except Exception as exc:
        print(f"[WARN] trigger_face_recognition could not emit signal: {exc}")

    return "Please show your face to the camera now. I'll verify your identity automatically using our secure face recognition system."
 
@function_tool
async def verify_employee_credentials(
    email: str | None = None,
    otp: str | None = None,
    name: str | None = None,
    employee_id: str | None = None,
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
        FlowState.FACE_RECOGNITION: "Please show your face to the camera for recognition.",
        FlowState.MANUAL_VERIFICATION: "Please provide your name and employee ID for verification.",
        FlowState.CREDENTIAL_CHECK: "Would you like to register your face for faster access next time?",
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
 
🔥 CRITICAL WAKE WORD BEHAVIOR:
- You START IN SLEEP MODE - DO NOT respond to anything except "Hey Clara"
- When you hear "Hey Clara" → IMMEDIATELY use start_reception_flow() tool
- Only after wake word detection → ask "Hello! Are you an Employee or a Visitor?"
- If user talks without saying "Hey Clara" first → IGNORE completely (return None)
 
FLOW SEQUENCE AFTER WAKE UP:
1. Wake Word: "Hey Clara" → use start_reception_flow() → ask employee/visitor question
2. Employee Classification: "I am employee" → use trigger_face_recognition() → face scan
3. Visitor Classification: "I am visitor" → use collect_visitor_info() → gather details
4. Face Recognition: Only happens AFTER employee classification
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
            # Core business tools  
            company_info,
            get_employee_details,
            listen_for_commands,
            get_weather,
            search_web,
            send_email,
            # log_and_notify_visitor,  # Removed - use collect_visitor_info instead
            # Face registration tools
            register_employee_face,
            check_face_registration_status,
            # Enhanced visitor tools
            capture_visitor_photo,
            get_visitor_log,
        ]

        # Filter out optional tools that may not be available (e.g., when dependencies are missing)
        tool_list = [tool for tool in tool_list if tool is not None]

        super().__init__(
            instructions=clara_instructions,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.7,
            ),
            tools=tool_list,
        )
       
    async def handle_message(self, message):
        """Override message handling to implement wake/sleep and flow logic"""
        # Get the text content from the message
        text_content = getattr(message, 'text', '') or str(message)
        print(f"🎤 Received message: '{text_content}'")

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
                    return message_out
        except Exception as _e:
            print(f"(non-fatal) verification sync error: {_e}")
        
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
                return combined_message  # Use combined message
            return state_response
            
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
                success, response, next_state = flow_manager.process_user_classification(text_content)
                if success:
                    print(f"✅ Classification successful: '{response}', next_state: {next_state.value}")
                    return response
                else:
                    print(f"❌ Classification failed: '{response}', staying in {session.current_state.value}")
                    return response
        
        # Context-aware fallback so we never send 'None' and keep a human feel
        try:
            lang = get_preferred_language()
            fb = _get_state_fallback(session, lang, include_default=False)
            if fb:
                print(f"🔄 Using context fallback for state {session.current_state.value}: '{fb}'")
                return fb
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
            return fb
        except Exception as err:
            print(f"❗ Unexpected LLM error: {err}")
            session = flow_manager.get_current_session()
            lang = get_preferred_language()
            fb = _get_state_fallback(session, lang, include_default=True)
            print("🔄 Falling back after unexpected LLM error")
            return fb

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
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('clara_debug.log')
        ]
    )
    logger = logging.getLogger("clara")
    
    logger.info("🔍 Starting Clara Agent with debug logging...")
    logger.debug(f"LiveKit URL: {os.getenv('LIVEKIT_URL')}")
    
    try:
        # Load shared state on startup
        from agent_state import load_state_from_file
        load_state_from_file()
        
        logger.info(f"🤖 Starting in room: {ctx.room.name}")
        logger.info("🔑 Checking environment variables...")
        
        # Verify required environment variables
        required_vars = ['LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info("✅ Environment variables verified")
        
        # Initialize the assistant
        logger.info("🚀 Initializing Clara assistant...")
        assistant = Assistant()
        
        logger.info("🔌 Creating AgentSession...")
        session = AgentSession(
            llm=assistant.llm,
            tts=assistant.tts,
            stt=assistant.stt,
            userdata=assistant
        )
        
        logger.info("🌐 Connecting to LiveKit room...")
        try:
            await session.start(assistant, room=ctx.room)
            logger.info("✅ Successfully connected to LiveKit room")
            logger.info("👂 Listening for 'Hey Clara'...")
        except Exception as e:
            logger.error(f"❌ Failed to connect to LiveKit: {str(e)}")
            logger.exception("Full error details:")
            raise
            
    except Exception as e:
        logger.critical(f"🔥 Critical error in Clara agent: {str(e)}", exc_info=True)
        raise
 
 
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