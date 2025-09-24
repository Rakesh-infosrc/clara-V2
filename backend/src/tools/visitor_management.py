import io
import os
import base64
import pandas as pd
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from livekit.agents import function_tool, RunContext
from .config import VISITOR_LOG, EMPLOYEE_CSV, get_gmail_credentials


@function_tool()
async def capture_visitor_photo(context: RunContext, visitor_name: str, image_bytes: bytes) -> str:
    """
    Capture and save visitor photo for security records
    """
    try:
        if not image_bytes or len(image_bytes) == 0:
            return "❌ No image data provided for visitor photo"
        
        # Create visitor photos directory
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        photos_dir = project_root / "data" / "visitor_photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        visitor_name = visitor_name or "Visitor"
        safe_name = "".join(c for c in str(visitor_name) if c.isalnum() or c in (' ', '-', '_')).rstrip() or "Visitor"
        filename = f"{safe_name}_{timestamp}.jpg"
        photo_path = photos_dir / filename
        
        # Save the image
        with open(photo_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"Visitor photo saved: {photo_path}")
        return f"✅ Photo captured and saved for visitor {visitor_name} at {photo_path}"
    except Exception as e:
        return f"❌ Error capturing visitor photo: {str(e)}"

@function_tool()
async def log_and_notify_visitor(
    context: RunContext, visitor_name: str, phone: str, purpose: str, meeting_employee: str, photo_captured: bool = False
) -> str:
    """
    Log visitor details, save photo, and notify the employee via email.
    Enhanced version with photo support.
    """
    try:
        # Append visitor log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "Visitor Name": visitor_name,
            "Phone": phone,
            "Purpose": purpose,
            "Meeting Employee": meeting_employee,
            "Photo Captured": "Yes" if photo_captured else "No",
            "Timestamp": timestamp,
        }

        try:
            df = pd.read_csv(VISITOR_LOG)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Visitor Name", "Phone", "Purpose", "Meeting Employee", "Photo Captured", "Timestamp"])

        df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        df.to_csv(VISITOR_LOG, index=False)

        # Lookup employee email
        df_employees = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = df_employees["Name"].str.strip().str.lower()
        emp_match = df_employees[df_employees["Name_norm"] == meeting_employee.strip().lower()]
        if emp_match.empty:
            return f"❌ Employee '{meeting_employee}' not found in records."

        emp_email = emp_match.iloc[0]["Email"]

        creds = get_gmail_credentials()
        if not creds['user'] or not creds['password']:
            return "❌ Email sending failed: Gmail credentials not configured."

        # Prepare email
        msg = MIMEMultipart()
        msg["From"] = creds['user']
        msg["To"] = emp_email
        msg["Subject"] = f"Visitor {visitor_name} is waiting for you at reception"

        photo_status = "Photo captured for security records" if photo_captured else "No photo captured"
        body = (
            f"Hi {meeting_employee},\n\n"
            f"A visitor has arrived to meet you.\n\n"
            f"Name: {visitor_name}\n"
            f"Phone: {phone}\n"
            f"Purpose: {purpose}\n"
            f"Security: {photo_status}\n"
            f"Arrived at: {timestamp}\n\n"
            "Please proceed to reception."
        )
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(creds['user'], creds['password'])
            server.sendmail(creds['user'], [emp_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Error sending visitor email: {str(e)}"

        return f"✅ Visitor {visitor_name} logged and {meeting_employee} has been notified by email."

    except Exception as e:
        return f"❌ Error in visitor flow: {str(e)}"


@function_tool()
async def get_visitor_log(context: RunContext, date_filter: str = None) -> str:
    """
    Get visitor log entries, optionally filtered by date
    """
    try:
        df = pd.read_csv(VISITOR_LOG)
        
        if date_filter:
            # Filter by date (format: YYYY-MM-DD)
            df = df[df['Timestamp'].str.contains(date_filter)]
        
        if df.empty:
            return "No visitor records found."
        
        # Format the output
        result = "Visitor Log:\n"
        for _, row in df.tail(10).iterrows():  # Show last 10 entries
            result += (
                f"- {row['Visitor Name']} | {row['Phone']} | "
                f"Meeting: {row['Meeting Employee']} | {row['Timestamp']}\n"
            )
        
        return result
        
    except FileNotFoundError:
        return "No visitor log file found."
    except Exception as e:
        return f"❌ Error reading visitor log: {str(e)}"
