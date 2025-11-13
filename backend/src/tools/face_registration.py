"""
Face Registration Tool

This tool allows new employees to register their faces after manual verification
"""

import io
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from livekit.agents import function_tool, RunContext

from .config import (
    EMPLOYEE_CSV,
    FACE_S3_BUCKET,
    FACE_IMAGE_BUCKET,
    FACE_IMAGE_PREFIX,
    FACE_IMAGE_EXTENSION,
)
from .face_recognition import get_face_encoding_data, save_face_encoding_data


_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _employee_image_bucket() -> str | None:
    return FACE_IMAGE_BUCKET or FACE_S3_BUCKET


def _build_employee_image_key(employee_id: str) -> str:
    prefix = (FACE_IMAGE_PREFIX or "").strip("/")
    ext = (FACE_IMAGE_EXTENSION or "png").lstrip(".")
    filename = f"{employee_id}.{ext}"
    return f"{prefix}/{filename}" if prefix else filename


def _guess_content_type(extension: str) -> str:
    ext = extension.lower()
    if ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"


def _upload_employee_image(employee_id: str, image_bytes: bytes) -> tuple[bool, str | None]:
    bucket = _employee_image_bucket()
    if not bucket or not image_bytes:
        return False, None

    key = _build_employee_image_key(employee_id)
    content_type = _guess_content_type((FACE_IMAGE_EXTENSION or "png").lstrip("."))

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=image_bytes,
            ContentType=content_type,
        )
        print(f"[FaceRegistration] Uploaded employee image to s3://{bucket}/{key}")
        return True, f"s3://{bucket}/{key}"
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"[FaceRegistration] Failed to upload employee image to S3 ({exc})")
    except Exception as exc:
        print(f"[FaceRegistration] Unexpected error uploading employee image: {exc}")
    return False, None


@function_tool()
async def register_employee_face(ctx: RunContext, employee_id: str, image_bytes: bytes) -> str:
    """
    Register a new employee's face after they've been manually verified.
    This updates the face encoding database.
    """
    try:
        print(f"Starting face registration for employee ID: {employee_id}")
        
        # Validate image data
        if not image_bytes or len(image_bytes) == 0:
            return "❌ No image data provided for face registration"
        
        # Load existing encodings
        encoding_data = get_face_encoding_data()
        if encoding_data:
            known_encodings = list(encoding_data.get("encodings", []))
            legacy_ids = (
                encoding_data.get("employee_ids")
                or encoding_data.get("ids")
                or encoding_data.get("names")
                or []
            )
            known_ids = list(legacy_ids)
        else:
            known_encodings = []
            known_ids = []
        
        # Check if employee ID exists in database
        try:
            df = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
            employee_match = df[df["EmployeeID"].str.strip().str.upper() == employee_id.strip().upper()]
            
            if employee_match.empty:
                return f"❌ Employee ID {employee_id} not found in employee database"
            
            employee_name = employee_match.iloc[0]["Name"]
        except Exception as e:
            return f" Error reading employee database: {str(e)}"
        
        # Check if face is already registered
        if employee_id in known_ids:
            return f"⚠️ Face already registered for {employee_name} (ID: {employee_id})"
        
        # Process the new face image
        try:
            np_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            print(f"Image loaded successfully. Shape: {np_image.shape}")
        except Exception as e:
            return f"❌ Error loading image: {str(e)}"
        
        # Encode the face
        encodings = face_recognition.face_encodings(np_image)
        if not encodings:
            return "❌ No face detected in the image. Please ensure your face is clearly visible and try again."
        
        if len(encodings) > 1:
            print(f"Multiple faces detected ({len(encodings)}), using the first one")
        
        new_encoding = encodings[0]
        print(f"Face encoding generated successfully for {employee_name}")
        
        # Quality check - compare with existing faces to avoid duplicates
        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, new_encoding)
            min_distance = min(distances) if distances else 1.0
            
            # If the face is too similar to an existing one, warn but still register
            if min_distance < 0.4:
                closest_id = known_ids[distances.argmin()]
                print(f"Warning: Face is similar to existing employee {closest_id} (distance: {min_distance})")
        
        # Add the new encoding
        known_encodings.append(new_encoding)
        known_ids.append(employee_id)
        
        # Save updated encodings
        updated_encoding_data = {
            "encodings": known_encodings,
            "employee_ids": known_ids
        }

        if not save_face_encoding_data(updated_encoding_data):
            return "❌ Error saving face encodings"

        image_uploaded, image_location = _upload_employee_image(employee_id, image_bytes)
        
        # Log the registration
        log_entry = {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "status": "registered"
        }
        print(f"Face registration completed: {log_entry}")
        
        return (
            "✅ Face registration successful! 🎉\n"
            f"Welcome {employee_name} (ID: {employee_id}).\n"
            "Your face has been registered for quick access in the future.\n"
            "Next time, you can simply show your face to the camera for instant verification."
        )
        
    except Exception as e:
        error_msg = f"Face registration error: {str(e)}"
        print(f"❌ {error_msg}")
        return (
            f"❌ {error_msg}\n"
            "Please contact the system administrator for assistance."
        )


@function_tool()
async def check_face_registration_status(ctx: RunContext, employee_id: str) -> str:
    """
    Check if an employee's face is already registered in the system
    """
    try:
        # Load existing encodings
        encoding_data = get_face_encoding_data()
        if not encoding_data:
            return "❌ Face recognition system not initialized"

        known_ids = (
            encoding_data.get("employee_ids")
            or encoding_data.get("ids")
            or encoding_data.get("names")
            or []
        )
        
        if employee_id in known_ids:
            return f" Face is registered for employee ID {employee_id}"
        else:
            return f" No face registered for employee ID {employee_id}"
        
    except Exception as e:
        return f" Error checking face registration status: {str(e)}"


@function_tool()
async def remove_face_registration(ctx: RunContext, employee_id: str) -> str:
    """
    Remove an employee's face registration (admin function)
    """
    try:
        # Load existing encodings
        encoding_data = get_face_encoding_data()
        if not encoding_data:
            return f" Face recognition system not initialized"

        known_encodings = list(encoding_data.get("encodings", []))
        legacy_ids = (
            encoding_data.get("employee_ids")
            or encoding_data.get("ids")
            or encoding_data.get("names")
            or []
        )
        known_ids = list(legacy_ids)
        
        if employee_id not in known_ids:
            return f"❌ No face registration found for employee ID {employee_id}"
        
        # Find and remove the employee's face
        index = known_ids.index(employee_id)
        known_encodings.pop(index)
        known_ids.pop(index)
        
        # Save updated encodings
        updated_encoding_data = {
            "encodings": known_encodings,
            "employee_ids": known_ids
        }

        if not save_face_encoding_data(updated_encoding_data):
            return "❌ Error saving face encodings"

        removed = f"s3://{_employee_image_bucket()}/{_build_employee_image_key(employee_id)}" if _employee_image_bucket() else None
        if removed:
            return f"✅ Face registration removed for employee ID {employee_id}. (Stored image will be overwritten on next registration: {removed})"
        return f"✅ Face registration removed for employee ID {employee_id}"

    except Exception as e:
        return f" Error removing face registration: {str(e)}"