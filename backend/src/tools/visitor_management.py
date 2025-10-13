import io
import os
import json
from datetime import datetime
from pathlib import Path

import unicodedata

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError
from livekit.agents import function_tool, RunContext

from .config import (
    get_visitor_photo_bucket,
    get_visitor_photo_prefix,
)
from .visitor_log_repository import (
    put_visitor_log,
    query_visitor_logs,
    mark_photo_captured,
)
from .sms_sender import send_sms_via_twilio
from .employee_repository import get_employee_by_name


_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _sanitize_visitor_name(visitor_name: str | None) -> str:
    raw = (visitor_name or "Visitor").strip()
    if not raw:
        return "Visitor"

    normalized = unicodedata.normalize("NFKD", raw)
    buffer: list[str] = []
    for ch in normalized:
        if ch.isalnum():
            buffer.append(ch)
        elif ch in {"-", "_"}:
            buffer.append(ch)
        elif ch.isspace():
            buffer.append("_")
    safe_name = "".join(buffer).strip("-_")
    return safe_name or "Visitor"


def _build_s3_key(visitor_name: str) -> tuple[str, str]:
    now = datetime.now()
    date_prefix = now.strftime("%Y_%m_%d")
    timestamp = now.strftime("%Y_%m_%d_%H%M%S")
    safe_name = _sanitize_visitor_name(visitor_name)
    filename = f"{safe_name}{timestamp}.png"
    root_prefix = get_visitor_photo_prefix()
    key_parts = [part for part in (root_prefix, date_prefix, filename) if part]
    s3_key = "/".join(key_parts)
    print(f"[VisitorPhoto] raw_name='{visitor_name}' sanitized='{safe_name}' s3_key='{s3_key}'")
    return s3_key, filename


def _upload_to_s3(image_bytes: bytes, visitor_name: str) -> tuple[str | None, str | None]:
    bucket = get_visitor_photo_bucket()
    if not bucket:
        return None, None

    s3_key, filename = _build_s3_key(visitor_name)

    try:
        client = _get_s3_client()
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=image_bytes,
            ContentType="image/png",
        )
        return s3_key, filename
    except (BotoCoreError, NoCredentialsError) as exc:
        print(f"❌ S3 upload failed ({exc}); falling back to local storage")
        return None, None


def _save_locally(image_bytes: bytes, visitor_name: str) -> str:
    project_root = Path(__file__).parent.parent.parent
    photos_dir = project_root / "data" / "visitor_image"
    photos_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    safe_name = _sanitize_visitor_name(visitor_name)
    filename = f"{safe_name}{now}.png"
    photo_path = photos_dir / filename
    print(f"[VisitorPhoto] raw_name='{visitor_name}' sanitized='{safe_name}' local_path='{photo_path}'")
    with open(photo_path, "wb") as f:
        f.write(image_bytes)
    print(f"Visitor photo saved locally: {photo_path}")
    return str(photo_path)


@function_tool()
async def capture_visitor_photo(context: RunContext, visitor_name: str, image_bytes: bytes) -> str:
    """
    Capture and persist visitor photo for security records, preferring S3 storage.
    """
    if not image_bytes:
        return "❌ No image data provided for visitor photo"

    visitor_name = visitor_name or "Visitor"

    # Try S3 upload first
    s3_key, filename = _upload_to_s3(image_bytes, visitor_name)

    if s3_key:
        storage_message = f"S3://{get_visitor_photo_bucket()}/{s3_key}"
        response = {
            "success": True,
            "visitor_name": visitor_name,
            "storage_type": "s3",
            "storage_location": storage_message,
            "s3_key": s3_key,
            "filename": filename,
            "message": f"✅ Photo captured and saved for visitor {visitor_name}: {storage_message}",
        }
        print(f"Visitor photo persisted: {storage_message}")
        return json.dumps(response)

    local_path = _save_locally(image_bytes, visitor_name)
    storage_message = local_path
    response = {
        "success": True,
        "visitor_name": visitor_name,
        "storage_type": "local",
        "storage_location": storage_message,
        "s3_key": None,
        "filename": Path(local_path).name,
        "message": f"✅ Photo captured and saved for visitor {visitor_name}: {storage_message}",
    }
    print(f"Visitor photo persisted: {storage_message}")
    return json.dumps(response)

@function_tool()
async def log_and_notify_visitor(
    context: RunContext,
    visitor_name: str,
    phone: str,
    purpose: str,
    meeting_employee: str,
    photo_captured: bool = False,
    photo_location: str | None = None,
) -> str:
    """
    Log visitor details, save photo, and notify the employee via email.
    Enhanced version with photo support.
    """
    try:
        # Append visitor log to DynamoDB
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Lookup employee contact details from DynamoDB
        employee_record = get_employee_by_name(meeting_employee)
        if not employee_record:
            return f"❌ Employee '{meeting_employee}' not found in records."

        raw_employee = employee_record.get("raw") or {}
        emp_email = (employee_record.get("email") or raw_employee.get("email") or "").strip()
        emp_phone = (employee_record.get("phone") or raw_employee.get("phone") or raw_employee.get("mobile") or "").strip()
        emp_id = employee_record.get("employee_id") or raw_employee.get("employee_id") or raw_employee.get("id")

        notification_sent = False
        notification_error: str | None = None
        notification_method: str | None = None
        notification_sid: str | None = None

        if not emp_email:
            notification_error = "Host email not found."

        if photo_captured and photo_location:
            photo_status = f"Photo captured for security records: {photo_location}"
        elif photo_captured:
            photo_status = "Photo captured for security records"
        else:
            photo_status = "No photo captured"

        message_text = (
            f"Visitor {visitor_name} ({phone or 'no phone'}) is here to meet "
            f"{meeting_employee} for {purpose or 'no purpose provided'}. "
            f"{photo_status}. Logged at {timestamp}."
        )

        # Try SMS first when phone is available
        if emp_phone:
            try:
                result = send_sms_via_twilio(
                    to_phone=emp_phone,
                    message=f"Visitor Alert: {message_text}",
                )
                notification_sent = True
                notification_method = "sms"
                notification_sid = result.split("SID:")[-1].strip(" )") if "SID" in result else None
            except RuntimeError as sms_error:
                notification_error = f"SMS notification failed: {sms_error}"

        if not notification_sent:
            # SMS missing or failed; try email when we have one
            if emp_email:
                from .email_sender import send_email_via_gmail

                try:
                    send_email_via_gmail(
                        to_email=emp_email,
                        subject=f"Visitor {visitor_name} is waiting at reception",
                        body=message_text,
                    )
                    notification_sent = True
                    notification_method = "email"
                except RuntimeError as email_error:
                    combined = f"Email notification failed: {email_error}"
                    notification_error = (
                        f"{notification_error}; {combined}" if notification_error else combined
                    )
            elif not notification_error:
                notification_error = "No phone or email available for host notification"

        if notification_sent:
            print(
                "[Visitor] Notification dispatched",
                {
                    "method": notification_method,
                    "employee": meeting_employee,
                    "employee_id": emp_id,
                    "phone": emp_phone,
                    "email": emp_email,
                    "message": message_text,
                    "sid": notification_sid,
                },
            )
        elif notification_error:
            print(
                "[Visitor] Notification failed",
                {
                    "employee": meeting_employee,
                    "employee_id": emp_id,
                    "phone": emp_phone,
                    "email": emp_email,
                    "error": notification_error,
                },
            )

        metadata_raw = {
            "host_email": emp_email or None,
            "host_phone": emp_phone or None,
            "employee_id": emp_id or None,
            "notification_sent": notification_sent,
            "notification_error": notification_error,
            "notification_method": notification_method if notification_sent else None,
            "notification_sid": notification_sid,
            "local_timestamp": timestamp,
            "photo_location": photo_location,
        }
        metadata = {k: v for k, v in metadata_raw.items() if v not in (None, "")}

        stored = put_visitor_log(
            visitor_name=visitor_name,
            phone=phone,
            purpose=purpose,
            meeting_employee=meeting_employee,
            photo_captured=photo_captured,
            metadata=metadata,
        )

        if not stored:
            return (
                "⚠️ Visitor logged locally and email sent, but failed to persist log to DynamoDB."
            )
        if notification_sent:
            return f"✅ Visitor {visitor_name} logged and {meeting_employee} has been notified via email."
        if notification_error:
            return f"⚠️ Visitor {visitor_name} logged but notification not sent: {notification_error}"
        return f"✅ Visitor {visitor_name} logged."

    except Exception as e:
        return f"❌ Error in visitor flow: {str(e)}"


@function_tool()
async def get_visitor_log(context: RunContext, date_filter: str = None) -> str:
    """
    Get visitor log entries, optionally filtered by date
    """
    try:
        items = query_visitor_logs(date_filter=date_filter, limit=10)

        if not items:
            return "No visitor records found."

        # Format the output
        result = "Visitor Log:\n"
        for item in items:
            result += (
                f"- {item.get('visitor_name', 'Unknown')} | {item.get('phone', '')} | "
                f"Meeting: {item.get('meeting_employee', '')} | {item.get('timestamp', '')}\n"
            )
        
        return result
        
    except Exception as e:
        return f"❌ Error reading visitor log: {str(e)}"


@function_tool()
async def mark_visitor_photo_captured(context: RunContext, visitor_name: str) -> str:
    """Mark the most recent visitor_log row for the given visitor today as Photo Captured = Yes.
    Useful when the info was logged first (without photo) and photo is captured later.
    """
    try:
        updated = mark_photo_captured(visitor_name)
        if not updated:
            return "No matching visitor entry for today to update."
        return "✅ Updated visitor log: Photo Captured = Yes"
    except Exception as e:
        return f"❌ Error updating visitor log: {str(e)}"
