import os
from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from livekit.agents import function_tool, RunContext

from .config import (
    get_twilio_account_sid,
    get_twilio_auth_token,
    get_twilio_phone_number,
    get_twilio_default_country_code,
)


def _normalize_phone_number(phone: str | None) -> str:
    """Return an E.164-ish phone number using the default country code when needed."""
    raw = (phone or "").strip()
    if not raw:
        return ""

    if raw.startswith("+"):
        return raw

    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return raw

    default_code = get_twilio_default_country_code() or ""
    default_code = default_code.strip()
    if default_code:
        if default_code.startswith("+"):
            return f"{default_code}{digits}"
        return f"+{default_code}{digits}"

    # No default country code configured; fall back to assuming the digits already include the
    # correct country code (prepend '+'). Twilio will validate and raise if incorrect.
    return f"+{digits}"


def send_sms_via_twilio(
    to_phone: str,
    message: str,
    from_phone: Optional[str] = None,
) -> str:
    """
    Send an SMS using Twilio API.

    Args:
        to_phone: The recipient's phone number (with country code)
        message: The SMS message to send
        from_phone: Optional sender phone number (uses configured default if not provided)

    Returns:
        str: Success message or raises RuntimeError on failure
    """
    account_sid = get_twilio_account_sid()
    auth_token = get_twilio_auth_token()
    from_number = from_phone or get_twilio_phone_number()
    to_number = _normalize_phone_number(to_phone)

    if not account_sid or not auth_token or not from_number:
        raise RuntimeError(
            "Twilio credentials not configured (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)"
        )

    if not to_number:
        raise RuntimeError("Recipient phone number not provided for Twilio SMS")

    # Initialize Twilio client
    client = Client(account_sid, auth_token)

    try:
        # Send SMS
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )

        print(
            "[SMS] Twilio message sent",
            {
                "to": to_number,
                "from": from_number,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "raw_recipient": to_phone,
            },
        )

        return f"SMS sent successfully to {to_number} (Message SID: {message_obj.sid})"

    except TwilioException as exc:
        error_msg = f"Twilio SMS failed: {exc}"
        print("[SMS] Twilio error", {"error": str(exc), "to": to_number, "raw_recipient": to_phone})
        raise RuntimeError(error_msg) from exc


@function_tool()
async def send_sms(
    context: RunContext,
    to_phone: str,
    message: str,
    from_phone: Optional[str] = None
) -> str:
    """
    Send an SMS using Twilio (async wrapper).
    """
    try:
        return send_sms_via_twilio(to_phone, message, from_phone)
    except Exception as exc:
        return f"Error sending SMS via Twilio: {str(exc)}"
