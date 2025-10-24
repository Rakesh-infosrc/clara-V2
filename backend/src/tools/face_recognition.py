import io
import pickle
import random
from typing import Any

import boto3
import face_recognition
import numpy as np
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from datetime import datetime
from livekit.agents import function_tool, RunContext

from .config import (
    FACE_S3_BUCKET,
    FACE_IMAGE_BUCKET,
    FACE_ENCODING_S3_KEY,
    otp_sessions,
)
from .employee_repository import get_employee_by_id
from .sms_sender import send_sms_via_sns
from .visitor_log_repository import put_visitor_log


_s3_client = None
_encoding_cache: dict[str, Any] | None = None
_employee_cache: dict[str, str] = {}


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _encoding_bucket() -> str | None:
    return FACE_S3_BUCKET or FACE_IMAGE_BUCKET


def _read_encoding_blob_from_s3() -> bytes | None:
    bucket = _encoding_bucket()
    key = FACE_ENCODING_S3_KEY

    if not bucket or not key:
        return None

    try:
        client = _get_s3_client()
        response = client.get_object(Bucket=bucket, Key=key)
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"[FaceRecognition] Failed to download encodings from S3 ({exc})")
        return None
    except Exception as exc:
        print(f"[FaceRecognition] Unexpected error fetching encodings from S3: {exc}")
        return None

    body = response.get("Body")
    if body is None:
        return None

    try:
        return body.read()
    except Exception as exc:
        print(f"[FaceRecognition] Failed to read S3 encoding payload: {exc}")
        return None


def get_face_encoding_data(force_reload: bool = False) -> dict[str, Any] | None:
    global _encoding_cache
    if not force_reload and _encoding_cache is not None:
        return _encoding_cache

    blob = _read_encoding_blob_from_s3()

    if blob is None:
        _encoding_cache = None
        return None

    try:
        data = pickle.loads(blob)
    except Exception as exc:
        print(f"[FaceRecognition] Failed to deserialize face encodings: {exc}")
        _encoding_cache = None
        return None

    _encoding_cache = data
    return data

def invalidate_face_encoding_cache() -> None:
    global _encoding_cache
    _encoding_cache = None


def save_face_encoding_data(data: dict[str, Any]) -> bool:
    if data is None:
        return False

    try:
        blob = pickle.dumps(data)
    except Exception as exc:
        print(f"[FaceRecognition] Failed to serialize face encodings: {exc}")
        return False

    bucket = _encoding_bucket()
    key = FACE_ENCODING_S3_KEY
    if not bucket or not key:
        print("[FaceRecognition] S3 bucket/key not configured; cannot save encodings")
        return False

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=blob,
            ContentType="application/octet-stream",
        )
        invalidate_face_encoding_cache()
        return True
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"[FaceRecognition] Failed to upload encodings to S3 ({exc})")
    except Exception as exc:
        print(f"[FaceRecognition] Unexpected error uploading encodings to S3: {exc}")

    return False


def _get_employee_name(employee_id: str) -> str | None:
    if not employee_id:
        return None

    key = employee_id.strip()
    if not key:
        return None

    if key in _employee_cache:
        return _employee_cache[key]

    name: str | None = None

    try:
        record = get_employee_by_id(key)
        if record:
            candidate = (record.get("name") or record.get("employee_id") or "").strip()
            if candidate:
                name = candidate
    except Exception as exc:
        print(f"[FaceRecognition] DynamoDB lookup failed for {key}: {exc}")

    if name:
        _employee_cache[key] = name

    return name


def _dispatch_face_verification_otp(employee_id: str, employee_name: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "otpSent": False,
        "message": None,
        "phone": None,
        "visitorLogId": None,
    }

    record = get_employee_by_id(employee_id)
    if not record:
        result["message"] = "Employee record not found for OTP dispatch"
        return result

    phone_number = (record.get("phone") or "").strip()
    if not phone_number:
        result["message"] = "Employee phone number not available"
        return result

    generated_otp = f"{random.randint(100000, 999999)}"
    otp_sessions[employee_id] = {
        "otp": generated_otp,
        "verified": False,
        "timestamp": datetime.utcnow().isoformat(),
        "employee_name": employee_name,
        "phone": phone_number,
    }

    message = (
        f"Hello {employee_name}, your Clara verification code is {generated_otp}. "
        "Use this OTP to complete your sign-in."
    )

    try:
        send_sms_via_sns(phone_number, message)
        result["otpSent"] = True
        result["message"] = "OTP sent via SNS"
        result["phone"] = phone_number
    except Exception as exc:
        result["message"] = f"Failed to send OTP: {exc}"

    try:
        metadata = {
            "employee_id": employee_id,
            "otp_sent": result["otpSent"],
            "phone": phone_number,
        }
        log_entry = put_visitor_log(
            visitor_name=employee_name,
            phone=phone_number,
            purpose="Employee face verification",
            meeting_employee=employee_name,
            photo_captured=False,
            metadata=metadata,
        )
        if log_entry and log_entry.get("visit_id"):
            result["visitorLogId"] = log_entry["visit_id"]
    except Exception as exc:
        print(f"[FaceRecognition] Failed to log visitor entry: {exc}")

    return result


# Pure function (can be used in API + agent)
# ---------------------------------------------------
def run_face_verify(image_bytes: bytes):
    """SECURE face verification with strict matching and comprehensive logging"""
    import time
    
    verification_id = int(time.time() * 1000)  # Unique ID for this verification
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n=== SECURITY VERIFICATION {verification_id} ===")
    print(f"Time: {timestamp}")
    print(f"Image size: {len(image_bytes)} bytes")
    
    try:
        
        # Validate image data
        if not image_bytes or len(image_bytes) == 0:
            return {"status": "error", "message": "No image data provided"}
        
        # Load image from bytes
        np_image = face_recognition.load_image_file(
            io.BytesIO(image_bytes)
        )
        

        encoding_data = get_face_encoding_data()
        if not encoding_data:
            return {"status": "error", "message": "Face database is unavailable"}

        known_encodings = encoding_data.get("encodings", [])
        known_ids = (
            encoding_data.get("employee_ids")
            or encoding_data.get("ids")
            or encoding_data.get("names")
            or []
        )
        print(f"Loaded {len(known_encodings)} encodings and {len(known_ids)} IDs")

        if not known_encodings or not known_ids:
            return {"status": "error", "message": "Face database is empty"}

        # Encode faces
        encodings = face_recognition.face_encodings(np_image)
        if not encodings:
            print("No face detected in the image")
            return {"status": "error", "message": "No face detected in image"}
        
        if len(encodings) > 1:
            print(f"Multiple faces detected ({len(encodings)}), using the first one")
            
        face_encoding = encodings[0]
        print(f"Face encoding generated successfully")

        # Compare with known encodings using a strict tolerance to avoid false matches
        print(f"Comparing against {len(known_encodings)} known faces...")
        tolerance = 0.55
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
        
        # Also get face distances for additional validation
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        print(f"Face distances: {face_distances}")
        
        # Find the best match (lowest distance)
        if len(face_distances) > 0:
            best_match_index = face_distances.argmin()
            best_distance = face_distances[best_match_index]
            print(f"Best match distance: {best_distance} (threshold: {tolerance})")

            # Security threshold matches the relaxed tolerance for consistent acceptance
            security_threshold = 0.55
            min_confidence_gap = 0.05

            if best_distance <= security_threshold and matches[best_match_index]:
                other_distances = [d for i, d in enumerate(face_distances) if i != best_match_index]
                confidence_gap = None
                if other_distances:
                    second_best = min(other_distances)
                    confidence_gap = second_best - best_distance
                    print(f"Confidence gap: {confidence_gap} (preferred: >{min_confidence_gap})")

                # Accept match if either gap is healthy or the best distance is very confident on its own
                gap_confident = confidence_gap is None or confidence_gap >= min_confidence_gap
                distance_confident = best_distance <= (security_threshold - 0.03)

                if gap_confident or distance_confident:
                    emp_id = known_ids[best_match_index]
                    emp_name = _get_employee_name(emp_id) or "Unknown"
                    if not gap_confident:
                        print("⚠️ Gap below preferred minimum but distance is confident; accepting match")
                    print(f"✅ Face match accepted: {emp_name} ({emp_id}) with distance {best_distance}")
                    otp_result = _dispatch_face_verification_otp(emp_id, emp_name)
                    return {
                        "status": "success",
                        "employeeId": emp_id,
                        "name": emp_name,
                        "otp": otp_result,
                    }
                else:
                    print("Confidence gap insufficient; rejecting match for safety")

        print("❌ SECURITY: Face verification FAILED - No secure match found")
        print(f"Best distance was: {best_distance if 'best_distance' in locals() else 'N/A'}")
        print("Reason: Face does not meet strict security requirements")
        return {"status": "error", "message": "Face not recognized - Security verification failed"}

    except Exception as e:
        error_msg = f"SECURITY ERROR in verification {verification_id}: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"=== END VERIFICATION {verification_id} ===\n")
        return {"status": "error", "message": "Verification system error"}
    
    finally:
        print(f"=== END VERIFICATION {verification_id} ===\n")


# ---------------------------------------------------
# Agent tool wrapper (for LiveKit LLM agent)
# ---------------------------------------------------
@function_tool
def face_verify(ctx: RunContext, image_bytes: bytes):
    return run_face_verify(image_bytes)


@function_tool()
async def face_login(ctx: RunContext, image_bytes: bytes) -> str:
    """
    Verify face → directly greet employee → grant full access to tools.
    Combines face recognition + manager visit greeting.
    """
    result = run_face_verify(image_bytes)

    if result.get("status") != "success":
        return f"❌ Face not recognized: {result.get('message')}"

    emp_id = result["employeeId"]
    emp_name = result["name"]

    return f"✅ Face recognized. Welcome {emp_name}!"

    # Default greeting if no manager visit today
    return f"✅ Welcome {emp_name}! You now have full access to all tools."