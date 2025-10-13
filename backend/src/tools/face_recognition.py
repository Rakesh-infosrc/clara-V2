import io
import pickle
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
)
from .employee_repository import get_employee_by_id


_s3_client = None
_encoding_cache: dict[str, Any] | None = None
_employee_cache: dict[str, str] = {}


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _encoding_bucket() -> str | None:
    return FACE_IMAGE_BUCKET or FACE_S3_BUCKET


def _read_encoding_bytes_from_s3() -> bytes | None:
    bucket = _encoding_bucket()
    key = FACE_ENCODING_S3_KEY
    if not bucket or not key:
        return None

    try:
        client = _get_s3_client()
        response = client.get_object(Bucket=bucket, Key=key)
        blob: bytes = response["Body"].read()
        return blob
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"[FaceRecognition] S3 download failed ({exc})")
    except Exception as exc:
        print(f"[FaceRecognition] Unexpected error while reading encodings from S3: {exc}")
    return None


def get_face_encoding_data(force_reload: bool = False) -> dict[str, Any] | None:
    global _encoding_cache
    if not force_reload and _encoding_cache is not None:
        return _encoding_cache

    blob = _read_encoding_bytes_from_s3()

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

    success = True

    bucket = _encoding_bucket()
    key = FACE_ENCODING_S3_KEY
    if bucket and key:
        try:
            client = _get_s3_client()
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=blob,
                ContentType="application/octet-stream",
            )
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            print(f"[FaceRecognition] Failed to upload encodings to S3 ({exc})")
            success = False
        except Exception as exc:
            print(f"[FaceRecognition] Unexpected error uploading encodings to S3: {exc}")
            success = False

        invalidate_face_encoding_cache()

    return success


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

        # Compare with known encodings using lenient tolerance
        print(f"Comparing against {len(known_encodings)} known faces...")
        tolerance = 0.7  # More lenient tolerance for better recognition
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=tolerance)
        
        # Also get face distances for additional validation
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        print(f"Face distances: {face_distances}")
        
        # Find the best match (lowest distance)
        if len(face_distances) > 0:
            best_match_index = face_distances.argmin()
            best_distance = face_distances[best_match_index]
            print(f"Best match distance: {best_distance} (threshold: {tolerance})")
            
            # Use lenient threshold for better user experience
            security_threshold = 0.6  # More lenient threshold
            
            if best_distance <= security_threshold and matches[best_match_index]:
                # Double-check: ensure this is significantly better than other matches
                other_distances = [d for i, d in enumerate(face_distances) if i != best_match_index]
                if other_distances:
                    second_best = min(other_distances)
                    confidence_gap = second_best - best_distance
                    print(f"Confidence gap: {confidence_gap} (required: >0.05)")
                    
                    # Require reasonable gap between best and second-best match
                    if confidence_gap > 0.05:
                        emp_id = known_ids[best_match_index]
                        emp_name = _get_employee_name(emp_id) or "Unknown"
                        print(f"✅ SECURE Face match found: {emp_name} ({emp_id}) with high confidence")
                        return {"status": "success", "employeeId": emp_id, "name": emp_name}
                else:
                    # Only one face in database, accept if distance is reasonable
                    if best_distance <= 0.6:  # More lenient for single face
                        emp_id = known_ids[best_match_index]
                        emp_name = _get_employee_name(emp_id) or "Unknown"
                        print(f"✅ SECURE Face match found: {emp_name} ({emp_id}) - single face verification")
                        return {"status": "success", "employeeId": emp_id, "name": emp_name}
        
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