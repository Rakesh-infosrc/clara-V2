import os
import uvicorn
import time
import random
import json
import warnings
from datetime import datetime
from fastapi import FastAPI, Query, File, UploadFile, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Suppress pkg_resources deprecation warning from face_recognition_models
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Ensure src package imports work when running from project root
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools import run_face_verify
from livekit import api  # Correct LiveKit import
from fastapi.responses import JSONResponse
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

# Load environment variables from .env
load_dotenv()

API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")

app = FastAPI()

@app.get("/token")
async def create_token(room: str, identity: str):
    try:
        # Mint a LiveKit access token for the frontend to join a room
        at = api.AccessToken()
        grants = api.VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True)
        token = at.with_grants(grants).with_identity(identity).to_jwt()
        return {"token": token, "url": LIVEKIT_URL}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to create token: {str(e)}"})

@app.post("/dispatch")
async def dispatch_agent(room: str = "Clara-room", agent_name: str = "clara-receptionist", metadata: str = ""):
    try:
        async with api.LiveKitAPI() as lk:
            req = CreateAgentDispatchRequest(agent_name=agent_name, room=room, metadata=metadata)
            dispatch = await lk.agent_dispatch.create_dispatch(req)
            return {"success": True, "dispatch_id": dispatch.id, "room": dispatch.room, "agent": dispatch.agent_name}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to dispatch agent: {str(e)}"})

# Pydantic models for request validation
class EmployeeVerificationRequest(BaseModel):
    name: str
    employee_id: str
    otp: str = None

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/face_verify")
async def face_verify_endpoint(image: UploadFile = File(...)):
    """Face verify and also notify the agent/flow on success.
    This mirrors the behavior of /face_login so the assistant recognizes the employee.
    """
    try:
        image_bytes = await image.read()
        result = run_face_verify(image_bytes)  # ✅ direct call

        if result.get("status") == "success":
            # Extract details
            emp_name = result.get("name")
            emp_id = result.get("employeeId")

            # 1) Update global agent verification state
            try:
                from agent_state import set_user_verified
                set_user_verified(emp_name, emp_id)
            except Exception as e:
                print(f"Warning: could not set agent verified state: {e}")

            # 2) Advance the flow manager session if any
            try:
                from flow_manager import flow_manager
                # Feed the same result dict to the flow manager
                flow_manager.process_face_recognition_result(result)
            except Exception as e:
                print(f"Warning: could not advance flow manager: {e}")

            return {
                "success": True,
                "verified": True,
                "message": f"✅ Face recognized. Welcome {emp_name}!",
                "employeeName": emp_name,
                "employeeId": emp_id,
                "access_granted": True,
                "status": "employee_verified"
            }
        else:
            return {
                "success": False,
                "verified": False,
                "message": result.get("message", "Face not recognized"),
                "access_granted": False,
                "status": "face_not_recognized"
            }

    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "message": f"Verification error: {str(e)}",
            "access_granted": False,
            "status": "error"
        }

@app.post("/face_login")
async def face_login_endpoint(image: UploadFile = File(...)):
    """Enhanced face login endpoint with full access grant"""
    try:
        image_bytes = await image.read()
        from tools.face_recognition import face_login
        result = await face_login(None, image_bytes)
        
        # Check if verification was successful
        if "✅" in result and ("Welcome" in result or "honored" in result):
            # Extract employee name from the result message
            import re
            name_match = re.search(r'Welcome ([^!,]+)', result)
            employee_name = name_match.group(1) if name_match else "Employee"
            
            # Notify the agent of successful verification
            from agent_state import set_user_verified
            set_user_verified(employee_name)
            
            return {
                "success": True,
                "verified": True,
                "message": result,
                "employeeName": employee_name,
                "access_granted": True,
                "status": "employee_verified"
            }
        else:
            return {
                "success": False,
                "verified": False,
                "message": "Face not recognized. Please provide your name and employee ID for manual verification.",
                "access_granted": False,
                "status": "face_not_recognized"
            }
    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "message": f"Verification error: {str(e)}",
            "access_granted": False,
            "status": "error"
        }

@app.post("/otp/send")
async def otp_send(request: EmployeeVerificationRequest):
    """Send OTP (or return dev OTP when DEV_MODE_OTP=true)."""
    try:
        from tools.employee_verification import get_employee_details
        msg = await get_employee_details(
            None,
            name=request.name,
            employee_id=request.employee_id,
        )
        return {"success": True, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"otp_send failed: {str(e)}"}


@app.post("/otp/verify")
async def otp_verify(request: EmployeeVerificationRequest):
    """Verify OTP and advance flow when successful."""
    try:
        from tools.employee_verification import get_employee_details
        from agent_state import set_user_verified
        from flow_manager import flow_manager, FlowState

        msg = await get_employee_details(
            None,
            name=request.name,
            employee_id=request.employee_id,
            otp=request.otp,
        )
        success = ("✅" in msg) and ("OTP verified" in msg or "Welcome" in msg)
        if success:
            set_user_verified(request.name, request.employee_id)
            session = flow_manager.get_current_session() or flow_manager.create_session()
            session = flow_manager.get_current_session()
            if session:
                session.user_data.update({"employee_name": request.name, "employee_id": request.employee_id})
                session.is_verified = True
                session.current_state = FlowState.EMPLOYEE_VERIFIED
                flow_manager.save_sessions()
        return {"success": success, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"otp_verify failed: {str(e)}"}


@app.post("/employee_verify")
async def employee_verify_endpoint(request: EmployeeVerificationRequest):
    """Manual employee verification with OTP"""
    try:
        from tools.employee_verification import get_employee_details
        from livekit.agents import RunContext
        
        # Create a mock context for the tool
        context = None  # The tool doesn't actually use the context parameter
        
        result = await get_employee_details(
            context,
            name=request.name,
            employee_id=request.employee_id,
            otp=request.otp,
        )
        
        # Parse the result to determine success/failure
        if " " in result:
            if "OTP verified" in result or "Welcome" in result:
                return {
                    "success": True,
                    "verified": True,
                    "message": result,
                    "otp_sent": False
                }
            elif "sent an OTP" in result:
                return {
                    "success": True,
                    "verified": False,
                    "message": result,
                    "otp_sent": True
                }
        
        return {
            "success": False,
            "verified": False,
            "message": result,
            "otp_sent": False
        }
        
    except Exception as e:
        return {
            "success": False,
            "verified": False,
            "message": f"Verification error: {str(e)}",
            "otp_sent": False
        }

@app.post("/notify_agent_verification")
async def notify_agent_verification(request: dict):
    """Notify the agent that a user has been verified via face recognition"""
    try:
        from agent_state import set_user_verified
        
        name = request.get('name')
        user_id = request.get('user_id')
        
        if name:
            set_user_verified(name, user_id)
            return {
                "success": True,
                "message": f"Agent notified of verification for {name}"
            }
        else:
            return {
                "success": False,
                "message": "Name is required for agent notification"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error notifying agent: {str(e)}"
        }


@app.post("/flow/start")
async def start_flow():
    """Start the reception flow"""
    try:
        from flow_manager import flow_manager
        success, message = flow_manager.process_wake_word_detected()
        return {
            "success": success,
            "message": message,
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error starting flow: {str(e)}"
        }


@app.post("/flow/classify_user")
async def classify_user(request: dict):
    """Classify user as employee or visitor"""
    try:
        from flow_manager import flow_manager
        user_input = request.get('user_input', '')
        success, message, next_state = flow_manager.process_user_classification(user_input)
        return {
            "success": success,
            "message": message,
            "next_state": next_state.value if next_state else None,
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error classifying user: {str(e)}"
        }


@app.post("/flow/face_recognition")
async def process_face_recognition_flow(image: UploadFile = File(...)):
    """Process face recognition for employees in the flow"""
    try:
        from flow_manager import flow_manager
        from tools import run_face_verify
        
        image_bytes = await image.read()
        face_result = run_face_verify(image_bytes)
\
        if face_result.get("status") == "success":
            try:
                from agent_state import set_user_verified
                emp_name = face_result.get("name")
                emp_id = face_result.get("employeeId")
                set_user_verified(emp_name, emp_id)
            except Exception as _e:
                print(f"Warning: could not sync agent state in /flow/face_recognition: {_e}")

        success, message, next_state = flow_manager.process_face_recognition_result(face_result)
        
        return {
            "success": success,
            "message": message,
            "next_state": next_state.value if next_state else None,
            "face_result": face_result,
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error in face recognition flow: {str(e)}"
        }


@app.post("/flow/manual_verification")
async def manual_verification_flow(request: dict):
    """Process manual employee verification using the async tool directly.
    This avoids running event loops inside flow_manager and ensures OTP is strictly checked.
    """
    try:
        from flow_manager import flow_manager, FlowState
        from tools.employee_verification import get_employee_details
        from agent_state import set_user_verified

        name = request.get('name')
        employee_id = request.get('employee_id')
        otp = request.get('otp')

        if not name or not employee_id:
            return {"success": False, "message": "Please provide both your name and employee ID.", "next_state": FlowState.MANUAL_VERIFICATION.value}

        # Ensure session exists and store provided credentials
        session = flow_manager.get_current_session()
        if not session:
            flow_manager.create_session()
            session = flow_manager.get_current_session()
        if session:
            session.user_data.update({"manual_name": name, "manual_employee_id": employee_id})
            flow_manager.save_sessions()

        if not otp:
            # Send/resend OTP (or show it in DEV mode)
            msg = await get_employee_details(None, name, employee_id, None)
            return {
                "success": False,
                "message": msg or "OTP has been sent to your registered email. Please provide the OTP to complete verification.",
                "next_state": FlowState.MANUAL_VERIFICATION.value,
                "flow_status": flow_manager.get_flow_status()
            }

        # Verify OTP
        msg = await get_employee_details(None, name, employee_id, otp)
        success = ("✅" in msg) and ("OTP verified" in msg or "Welcome" in msg)
        if success:
            # Mark verified and move to credential check (offer face registration)
            if session:
                session.user_data["verification_method"] = "manual_with_otp"
                session.is_verified = True
                session.current_state = FlowState.CREDENTIAL_CHECK
                flow_manager.save_sessions()
            try:
                set_user_verified(name, employee_id)
            except Exception as _e:
                print(f"Warning: could not sync agent state after OTP verify: {_e}")

            return {
                "success": True,
                "message": f"Credentials verified! Welcome {name}. Would you like to register your face for faster access next time? (Yes/No)",
                "next_state": FlowState.CREDENTIAL_CHECK.value,
                "flow_status": flow_manager.get_flow_status()
            }
        else:
            return {
                "success": False,
                "message": msg or "OTP verification failed.",
                "next_state": FlowState.MANUAL_VERIFICATION.value,
                "flow_status": flow_manager.get_flow_status()
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error in manual verification: {str(e)}"
        }


@app.post("/flow/face_registration_choice")
async def face_registration_choice(request: dict):
    """Handle face registration choice after manual verification"""
    try:
        from flow_manager import flow_manager
        
        register_face = request.get('register_face', False)
        success, message, next_state = flow_manager.process_face_registration_choice(register_face)
        
        return {
            "success": success,
            "message": message,
            "next_state": next_state.value if next_state else None,
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing face registration choice: {str(e)}"
        }


@app.post("/flow/register_face")
async def register_employee_face_endpoint(image: UploadFile = File(...), employee_id: str | None = None):
    """Register employee face after manual verification.
    If employee_id is omitted, try to read it from the current flow session.
    """
    try:
        from tools.face_registration import register_employee_face as register_face_tool
        from livekit.agents import RunContext
        from flow_manager import flow_manager
        
        # Fallback to current session's employee id
        if not employee_id:
            session = flow_manager.get_current_session()
            if session:
                employee_id = (
                    session.user_data.get("manual_employee_id")
                    or session.user_data.get("employee_id")
                )
        
        if not employee_id:
            return {
                "success": False,
                "message": "Employee ID is required for face registration"
            }
        
        image_bytes = await image.read()
        result = await register_face_tool(None, employee_id, image_bytes)
        
        success = "✅" in result
        if success:
            # Use the proper flow completion handler
            try:
                success_result, completion_message, next_state = flow_manager.process_face_registration_completion(True, result)
                from flow_signal import post_signal
                post_signal("registration_complete", {"message": completion_message})
            except Exception as _e:
                print(f"Warning: could not advance flow after registration: {_e}")
        else:
            # Handle registration failure
            try:
                success_result, completion_message, next_state = flow_manager.process_face_registration_completion(False, result)
            except Exception as _e:
                print(f"Warning: could not handle registration failure: {_e}")
        
        return {
            "success": success,
            "message": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error registering face: {str(e)}"
        }


@app.post("/flow/visitor_info")
async def collect_visitor_info(request: dict):
    """Collect visitor information"""
    try:
        from flow_manager import flow_manager
        
        name = request.get('name')
        phone = request.get('phone')
        purpose = request.get('purpose')
        host_employee = request.get('host_employee')
        
        success, message, next_state = await flow_manager.process_visitor_info(name, phone, purpose, host_employee)
        
        return {
            "success": success,
            "message": message,
            "next_state": next_state.value if next_state else None,
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error collecting visitor info: {str(e)}"
        }


@app.post("/flow/visitor_photo")
async def capture_visitor_photo_flow(
    request: Request,
    image: UploadFile = File(None),
    file: UploadFile = File(None)
):
    """Capture visitor photo and complete visitor flow"""
    try:
        from flow_manager import flow_manager
        from tools.visitor_management import (
    capture_visitor_photo,
    log_and_notify_visitor,
    mark_visitor_photo_captured,
)

        # Pick whichever file field was provided
        upload = image or file
        if upload is None:
            form = await request.form()
            for _, v in form.items():
                if hasattr(v, "filename"):
                    upload = v
                    break
        if upload is None:
            return {"success": False, "message": "No image file uploaded (try field name 'image' or 'file')"}

        # Get visitor name from session
        session = flow_manager.get_current_session()
        visitor_name = session.user_data.get('visitor_name') if session else None
        if not visitor_name:
            try:
                form = form if 'form' in locals() else await request.form()
                visitor_name = form.get('visitor_name')
            except:
                pass
        visitor_name = visitor_name or "Visitor"

        # Capture and save the actual image
        image_bytes = await upload.read()
        photo_result_raw = await capture_visitor_photo(None, visitor_name, image_bytes)
        photo_result = {}
        try:
            photo_result = json.loads(photo_result_raw) if isinstance(photo_result_raw, str) else photo_result_raw
        except Exception:
            photo_result = {"success": True, "message": photo_result_raw, "storage_location": None}

        if photo_result and isinstance(photo_result, dict):
            session.user_data["photo_location"] = photo_result.get("storage_location")
            session.user_data["photo_storage_type"] = photo_result.get("storage_type")
            session.user_data["photo_filename"] = photo_result.get("filename")
            flow_manager.save_sessions()

        visitor_phone = session.user_data.get('visitor_phone') if session else ""
        visitor_purpose = session.user_data.get('visitor_purpose') if session else ""
        host_employee = session.user_data.get('host_employee') if session else ""
        photo_location = session.user_data.get("photo_location") if session else None

        # Log visitor and notify host now that photo is captured
        if visitor_name and host_employee:
            try:
                log_result = await log_and_notify_visitor(
                    None,
                    visitor_name,
                    visitor_phone or "",
                    visitor_purpose or "",
                    host_employee,
                    True,
                    photo_location,
                )
                print(f"[VisitorPhoto] log_and_notify_visitor -> {log_result}")
            except Exception as log_exc:
                print(f"Warning: log_and_notify_visitor failed: {log_exc}")
        else:
            print("Warning: Skipping visitor log/notify due to missing visitor or host info")

        # Mark visitor log as photo captured
        try:
            await mark_visitor_photo_captured(None, visitor_name)
        except Exception as _e:
            print(f"Warning: could not update visitor log photo flag: {_e}")

        # Advance flow to completion
        success, message, next_state = flow_manager.process_visitor_face_capture(True)

        return {
            "success": success,
            "message": message,
            "next_state": next_state.value if next_state else None,
            "photo_result": photo_result,
            "filename": f"{visitor_name}{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "flow_status": flow_manager.get_flow_status()
        }
    except Exception as e:
        return {"success": False, "message": f"Error capturing visitor photo: {str(e)}"}

@app.get("/flow/status")
async def get_flow_status():
    """Get current flow status"""
    try:
        from flow_manager import flow_manager
        status = flow_manager.get_flow_status()
        return {
            "success": True,
            "flow_status": status
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting flow status: {str(e)}"
        }


@app.post("/post_signal")
async def post_signal_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        return {"success": False, "error": f"Invalid JSON payload: {str(e)}"}

    name = body.get("name") if isinstance(body, dict) else None
    if not name:
        return {"success": False, "error": "Signal name is required"}

    payload = body.get("payload") if isinstance(body, dict) else None
    if payload is not None and not isinstance(payload, dict):
        return {"success": False, "error": "Signal payload must be an object"}

    try:
        from flow_signal import post_signal
        post_signal(name, payload)
        return {"success": True, "name": name, "payload": payload or {}}
    except Exception as e:
        return {"success": False, "error": f"Error posting signal: {str(e)}"}

@app.get("/get_signal")
async def get_signal():
    """Get signals from the flow manager for frontend communication"""
    try:
        from flow_signal import get_signal
        signal = get_signal(clear=False)  # Get but don't clear the signal immediately
        return signal if signal else {}
    except Exception as e:
        return {
            "error": f"Error getting signal: {str(e)}"
        }

@app.post("/clear_signal")
async def clear_signal():
    """Clear the current signal after frontend has processed it"""
    try:
        from flow_signal import get_signal
        signal = get_signal(clear=True)  # Clear the signal
        return {"success": True, "cleared": signal is not None}
    except Exception as e:
        return {
            "success": False,
            "error": f"Error clearing signal: {str(e)}"
        }


@app.post("/flow/end")
async def end_flow_session():
    """End the current flow session"""
    try:
        from flow_manager import flow_manager
        message = flow_manager.end_session()
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error ending flow session: {str(e)}"
        }


@app.get("/get-token")
def get_token(identity: str = Query(...), room: str = "Clara-room"):
    """
    Generate a LiveKit access token for the given identity.
    Handles reconnects by generating unique identities per session.
    """
    try:
        # Generate a unique session identity
        session_identity = f"{identity}_{random.randint(1000,9999)}"

        # Create AccessToken
        at = api.AccessToken(API_KEY, API_SECRET)
        at.identity = session_identity

        # Set token expiration to 1 hour from now
        at.expires_at = int(time.time()) + 3600

        # Add video grant to allow joining the room
        video_grants = api.VideoGrants(room=room, room_join=True)
        at.with_grants(video_grants)

        # Generate JWT token
        token = at.to_jwt()

        print(f"✅ Issued token for {session_identity} in room {room}")
        return {"token": token, "url": LIVEKIT_URL, "room": room}

    except Exception as e:
        print("❌ Error issuing token:", str(e))
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
