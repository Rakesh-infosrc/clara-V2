import smtplib
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from livekit.agents import function_tool, RunContext
from .config import get_gmail_credentials


@function_tool()
async def send_email(
    context: RunContext, to_email: str, subject: str, message: str, cc_email: Optional[str] = None
) -> str:
    """Send an email through Gmail."""
    try:
        creds = get_gmail_credentials()
        if not creds['user'] or not creds['password']:
            return "❌ Email sending failed: Gmail credentials not configured."

        msg = MIMEMultipart()
        msg["From"] = creds['user']
        msg["To"] = to_email
        msg["Subject"] = subject
        if cc_email:
            msg["Cc"] = cc_email
        msg.attach(MIMEText(message, "plain"))

        recipients = [to_email] + ([cc_email] if cc_email else [])

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(creds['user'], creds['password'])
        server.sendmail(creds['user'], recipients, msg.as_string())
        server.quit()

        return f"✅ Email sent successfully to {to_email}"

    except Exception as e:
        return f"❌ Error sending email: {str(e)}"