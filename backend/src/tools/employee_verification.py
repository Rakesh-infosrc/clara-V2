import random
from datetime import datetime
from typing import Optional

from livekit.agents import function_tool, RunContext

from .config import (
    otp_sessions,
    is_dev_mode_otp,
    get_gmail_user,
    get_gmail_app_password,
)
from .employee_repository import get_employee_by_email, get_employee_by_id
from .manager_visit_repository import get_manager_visit
from .email_sender import send_email_via_gmail
from .sms_sender import send_sms_via_twilio

def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _load_employee_record(
    email: str | None,
    employee_id: str | None = None,
    fallback_name: Optional[str] = None,
    fallback_employee_id: Optional[str] = None,
) -> Optional[dict]:
    raw_email = (email or "").strip()
    raw_employee_id = (employee_id or "").strip()

    record = None
    if raw_email:
        record = get_employee_by_email(raw_email)

    if not record and raw_employee_id:
        record = get_employee_by_id(raw_employee_id)

    if not record:
        return None

    record_email = record.get("email") or raw_email
    email_key = _normalize_email(record_email)
    if email_key:
        record["email"] = email_key
    if fallback_name and not record.get("name"):
        record["name"] = fallback_name
    if fallback_employee_id and not record.get("employee_id"):
        record["employee_id"] = fallback_employee_id or raw_employee_id
    return record


def _prepare_session(email_key: str, record: dict) -> None:
    otp_sessions[email_key] = {
        "otp": None,
        "verified": False,
        "attempts": 0,
        "name": record.get("name"),
        "employee_id": record.get("employee_id"),
        "delivery_method": None,
    }


def _issue_otp(email_key: str, record: dict) -> str:
    if email_key not in otp_sessions:
        _prepare_session(email_key, record)

    generated_otp = str(random.randint(100000, 999999))
    session = otp_sessions[email_key]
    session["otp"] = generated_otp
    session["verified"] = False
    session["attempts"] = 0
    session["name"] = record.get("name")
    session["employee_id"] = record.get("employee_id")
    session["delivery_method"] = None

    emp_name = record.get("name") or "there"
    emp_phone = record.get("phone") or record.get("mobile")

    if is_dev_mode_otp():
        return (
            f"✅ [DEV MODE] OTP generated for {emp_name}. "
            f"Use this OTP to verify: {generated_otp}"
        )

    # Try SMS first, fall back to email if no phone number
    if emp_phone:
        try:
            sms_message = f"Hello {emp_name}, your OTP is: {generated_otp}"
            send_sms_via_twilio(
                to_phone=emp_phone,
                message=sms_message,
            )
            delivery_method = "sms"
            delivery_details = f"to {emp_phone}"
        except RuntimeError as sms_error:
            print(f"[OTP] SMS failed, trying email: {sms_error}")
            # Fall back to email if SMS fails
            gmail_user = get_gmail_user()
            gmail_password = get_gmail_app_password()
            if gmail_user and gmail_password:
                try:
                    email_message = f"Hello {emp_name}, your OTP is: {generated_otp}"
                    send_email_via_gmail(
                        to_email=email_key,
                        subject="Your One-Time Password (OTP)",
                        body=email_message,
                    )
                    delivery_method = "email"
                    delivery_details = f"to {email_key}"
                except RuntimeError as email_error:
                    return f"❌ Both SMS and email sending failed. SMS: {sms_error}. Email: {email_error}"
            else:
                return f"❌ SMS failed and email credentials not configured: {sms_error}"
    else:
        # No phone number, try email
        gmail_user = get_gmail_user()
        gmail_password = get_gmail_app_password()
        if not gmail_user or not gmail_password:
            return "❌ No phone number found and email credentials not configured."

        email_message = f"Hello {emp_name}, your OTP is: {generated_otp}"
        try:
            # Wait, I need to import the email sender back
            from .email_sender import send_email_via_gmail
            send_email_via_gmail(
                to_email=email_key,
                subject="Your One-Time Password (OTP)",
                body=email_message,
            )
            delivery_method = "email"
            delivery_details = f"to {email_key}"
        except RuntimeError as email_error:
            return f"❌ Email sending failed: {email_error}"

    session["delivery_method"] = delivery_method
    session["delivery_log"] = {
        "timestamp": datetime.now().isoformat(),
        "delivery_method": delivery_method,
        "details": delivery_details,
        "otp": generated_otp,
        "employee": emp_name,
    }
    print(
        f"[OTP] {delivery_method.upper()} dispatched",
        {
            "delivery_method": delivery_method,
            "details": delivery_details,
            "employee": emp_name,
            "otp": generated_otp,
        },
    )
    return f"✅ Hi {emp_name}, I sent an OTP via {delivery_method} ({delivery_details}). Please tell me the OTP now."


def _manager_visit_message(emp_id: Optional[str], emp_name: str, default_message: str) -> str:
    if not emp_id:
        return default_message

    today = datetime.now().strftime("%Y-%m-%d")
    record = get_manager_visit(emp_id, today)
    if not record:
        return default_message

    office = record.get("office") or record.get("Office") or "our office"
    manager_name = record.get("manager_name") or record.get("ManagerName")

    parts = [
        "✅ OTP verified.",
        f"Welcome {emp_name}!",
        f"Hope your visit to our {office} office goes smoothly.",
    ]
    if manager_name:
        parts.append(f"Your meeting with {manager_name} is confirmed.")
    parts.append("Let me know if you need any assistance while you're here.")

    return "\n".join(parts)


def _verify_otp(email_key: str, otp: str, record: dict) -> str:
    session = otp_sessions.get(email_key)
    if not session:
        return "❌ No OTP session found. Please request OTP first."

    attempts = session.get("attempts", 0)
    if attempts >= 3:
        _prepare_session(email_key, record)
        return "❌ Too many failed OTP attempts. Restart verification."

    provided_otp = str(otp or "").strip()
    if not provided_otp:
        return "❌ Please provide the OTP that was sent to your email."

    saved_otp = session.get("otp")
    if saved_otp and provided_otp == saved_otp:
        session["verified"] = True
        emp_name = record.get("name") or session.get("name") or "Employee"
        emp_id = record.get("employee_id") or session.get("employee_id")
        default_message = f"✅ OTP verified. Welcome {emp_name}!"
        return _manager_visit_message(emp_id, emp_name, default_message)

    session["attempts"] = attempts + 1
    remaining = max(0, 3 - session["attempts"])
    return f"❌ OTP incorrect. Attempts left: {remaining}."


@function_tool()
async def get_employee_details(
    context: RunContext,
    email: str | None = None,
    name: str | None = None,
    employee_id: str | None = None,
    otp: str | None = None,
) -> str:
    """Send or verify an OTP for the employee associated with ``email``."""

    raw_email = (email or "").strip()
    raw_employee_id = (employee_id or "").strip()
    if not raw_employee_id:
        return "❌ Please provide your employee ID so I can fetch your registered email."

    record = _load_employee_record(raw_email, raw_employee_id, fallback_name=name, fallback_employee_id=employee_id)
    if not record:
        return "❌ Employee ID not found in employee records. Please recheck it."

    email_key = _normalize_email(record.get("email") or raw_email)
    if not email_key:
        return "❌ Unable to verify without a valid email address on file."

    if otp is None or not str(otp).strip():
        return _issue_otp(email_key, record)

    return _verify_otp(email_key, otp, record)


def send_otp_sync(email: str | None, employee_id: str | None = None) -> tuple[str, Optional[dict]]:
    """Synchronous helper to send an OTP (used by flow manager).

    Returns a tuple containing the message and the resolved employee record (if found).
    """

    raw_email = (email or "").strip()
    raw_employee_id = (employee_id or "").strip()
    if not raw_employee_id:
        return "❌ Please provide your employee ID so I can send the OTP to your registered email.", None

    record = _load_employee_record(raw_email, raw_employee_id)
    if not record:
        return "❌ Employee ID not found in employee records. Please recheck it.", None

    email_key = _normalize_email(record.get("email") or raw_email)
    if not email_key:
        return "❌ Unable to verify without a valid email address on file.", None

    return _issue_otp(email_key, record), record


def verify_otp_sync(email: str | None, otp: str | None, employee_id: str | None = None) -> str:
    """Synchronous helper to verify an OTP (used by flow manager)."""

    raw_email = (email or "").strip()
    raw_employee_id = (employee_id or "").strip()
    if not raw_employee_id:
        return "❌ Please provide your employee ID so I can verify the OTP."

    record = _load_employee_record(raw_email, raw_employee_id)
    if not record:
        return "❌ Employee ID not found in employee records. Please recheck it."

    email_key = _normalize_email(record.get("email") or raw_email)
    if not email_key:
        return "❌ Unable to verify without a valid email address on file."

    provided_otp = (otp or "").strip()
    if not provided_otp:
        return "❌ Please provide the OTP that was sent to your email."

    return _verify_otp(email_key, provided_otp, record)
