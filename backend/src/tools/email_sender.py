from typing import Optional

import smtplib
from email.message import EmailMessage
from smtplib import SMTPAuthenticationError, SMTPException
from livekit.agents import function_tool, RunContext

from .config import get_gmail_user, get_gmail_app_password


def _build_email_message(
    sender: str,
    to_email: str,
    subject: str,
    body: str,
    cc_email: Optional[str] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_email
    if cc_email:
        msg["Cc"] = cc_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send_email_via_gmail(
    to_email: str,
    subject: str,
    body: str,
    cc_email: Optional[str] = None,
) -> str:
    sender = get_gmail_user()
    app_password = get_gmail_app_password()

    if not sender or not app_password:
        raise RuntimeError("Gmail credentials not configured (GMAIL_USER / GMAIL_APP_PASSWORD)")

    msg = _build_email_message(sender, to_email, subject, body, cc_email)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
    except SMTPAuthenticationError as exc:
        code = exc.smtp_code
        message = ""
        if exc.smtp_error:
            try:
                message = exc.smtp_error.decode("utf-8", errors="ignore")
            except AttributeError:
                message = str(exc.smtp_error)
        detail = message or "authentication failed"
        print("[Email] Gmail authentication failed", {"code": code, "detail": detail})
        raise RuntimeError(f"Gmail authentication failed (code {code}): {detail}") from exc
    except SMTPException as exc:
        print("[Email] Gmail SMTP error", {"error": str(exc)})
        raise RuntimeError(f"Gmail SMTP error: {exc}") from exc

    return f"Email sent successfully to {to_email}"


@function_tool()
async def send_email(
    context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None
) -> str:
    """Send an email using Gmail SMTP credentials."""
    try:
        return send_email_via_gmail(to_email, subject, message, cc_email)
    except Exception as exc:
        return f"Error sending email via Gmail: {str(exc)}"