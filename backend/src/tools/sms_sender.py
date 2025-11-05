import os
from datetime import datetime
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from livekit.agents import function_tool, RunContext

from .config import (
    get_sns_access_key_id,
    get_sns_secret_access_key,
    get_sns_region,
    get_sns_sender_id,
    get_sns_sms_type,
    get_sns_entity_id,
    get_sns_template_id,
    get_default_sms_country_code,
)
from .config import is_dev_mode_otp


_sns_client: Optional[Any] = None


def _get_sns_client():
    global _sns_client
    if _sns_client is None:
        client_kwargs = {"region_name": get_sns_region()}
        access_key = get_sns_access_key_id()
        secret_key = get_sns_secret_access_key()
        if access_key and secret_key:
            client_kwargs.update(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
        _sns_client = boto3.client("sns", **client_kwargs)
    return _sns_client


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

    default_code = get_default_sms_country_code() or ""
    default_code = default_code.strip()
    if default_code:
        if default_code.startswith("+"):
            return f"{default_code}{digits}"
        return f"+{default_code}{digits}"

    return f"+{digits}"


def send_sms_via_sns(
    to_phone: str,
    message: str,
    sender_id: Optional[str] = None,
    sms_type: Optional[str] = None,
    *,
    region_override: Optional[str] = None,
    access_key_override: Optional[str] = None,
    secret_key_override: Optional[str] = None,
) -> str:
    """Send an SMS using AWS SNS."""

    to_number = _normalize_phone_number(to_phone)
    if not to_number:
        raise RuntimeError("Recipient phone number not provided for SMS")

    try:
        if region_override or access_key_override or secret_key_override:
            override_kwargs = {"region_name": (region_override or get_sns_region())}
            if access_key_override and secret_key_override:
                override_kwargs.update(
                    aws_access_key_id=access_key_override,
                    aws_secret_access_key=secret_key_override,
                )
            client = boto3.client("sns", **override_kwargs)
        else:
            client = _get_sns_client()
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize SNS client: {exc}") from exc

    attributes: dict[str, str] = {}

    resolved_sender = sender_id or get_sns_sender_id()
    resolved_type = (sms_type or get_sns_sms_type() or "Transactional").title()
    if resolved_type not in {"Transactional", "Promotional"}:
        resolved_type = "Transactional"

    include_reserved_attributes = not is_dev_mode_otp()

    if include_reserved_attributes and resolved_sender:
        attributes["AWS.SNS.SMS.SenderID"] = resolved_sender
    if include_reserved_attributes:
        attributes["AWS.SNS.SMS.SMSType"] = resolved_type

        entity_id = get_sns_entity_id()
        if entity_id:
            attributes["AWS.SNS.SMS.EntityId"] = entity_id

        template_id = get_sns_template_id()
        if template_id:
            attributes["AWS.SNS.SMS.TemplateId"] = template_id

    if not include_reserved_attributes:
        attributes["SMSType"] = resolved_type
    try:
        response = client.publish(
            PhoneNumber=to_number,
            Message=message,
            MessageAttributes={
                key: {
                    "DataType": "String",
                    "StringValue": value,
                }
                for key, value in attributes.items()
            },
        )
    except (BotoCoreError, ClientError) as exc:
        print("[SMS] SNS publish failed", {"error": str(exc), "to": to_number, "raw_recipient": to_phone})
        raise RuntimeError(f"SNS SMS failed: {exc}") from exc

    message_id = response.get("MessageId")
    print(
        "[SMS] SNS message sent",
        {
            "to": to_number,
            "sender_id": resolved_sender,
            "sms_type": resolved_type,
            "message_id": message_id,
            "raw_recipient": to_phone,
        },
    )

    return f"SMS sent successfully to {to_number} (Message ID: {message_id})"


def build_visitor_notification_message(
    *,
    visitor_name: str,
    visitor_phone: Optional[str],
    purpose: Optional[str],
    meeting_employee: str,
    timestamp: Optional[str] = None,
    photo_status: Optional[str] = None,
) -> str:
    visitor_phone = (visitor_phone or "no phone").strip() or "no phone"
    purpose = (purpose or "no purpose provided").strip() or "no purpose provided"
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    photo_status = photo_status or "No photo captured"

    lines = [
        f"Visitor Log Entry - {timestamp}",
        f"Visitor: {visitor_name}",
        f"Contact: {visitor_phone}",
        f"Host: {meeting_employee}",
        f"Purpose: {purpose}",
        photo_status,
    ]
    return "\n".join(line for line in lines if line)


def send_visitor_notification_sms(
    *,
    host_phone: str,
    visitor_name: str,
    visitor_phone: Optional[str],
    purpose: Optional[str],
    meeting_employee: str,
    timestamp: Optional[str] = None,
    photo_status: Optional[str] = None,
    sender_id: Optional[str] = None,
    sms_type: Optional[str] = None,
) -> str:
    message = build_visitor_notification_message(
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        purpose=purpose,
        meeting_employee=meeting_employee,
        timestamp=timestamp,
        photo_status=photo_status,
    )
    return send_sms_via_sns(host_phone, message, sender_id, sms_type)


@function_tool()
async def send_sms(
    context: RunContext,
    to_phone: str,
    message: str,
    sender_id: Optional[str] = None,
    sms_type: Optional[str] = None,
) -> str:
    """Send an SMS using AWS SNS."""

    try:
        return send_sms_via_sns(to_phone, message, sender_id, sms_type)
    except Exception as exc:
        return f"Error sending SMS via SNS: {str(exc)}"
