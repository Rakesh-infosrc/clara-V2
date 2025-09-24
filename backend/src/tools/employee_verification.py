import re
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from livekit.agents import function_tool, RunContext
from .config import EMPLOYEE_CSV, MANAGER_VISIT_CSV, otp_sessions, get_gmail_credentials


@function_tool()
async def get_employee_details(
    context: RunContext, name: str, employee_id: str, otp: str = None
) -> str:
    """
    Secure Employee Verification Tool:
    - Validate Name + EmployeeID strictly.
    - OTP only after valid check.
    - Resend OTP if user asks again before verifying.
    - Retry limit: 3 OTP attempts.
    - After success, check manager_visit.csv → give special greeting.
    """
    try:
        # ---------------- Load Employee Database ----------------
        df = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
        df["Name_norm"] = df["Name"].astype(str).str.strip().str.lower()
        df["EmployeeID_norm"] = df["EmployeeID"].astype(str).str.strip().str.upper()

        # Normalize user input
        name_norm = re.sub(r"\s+", " ", name).strip().lower()
        empid_norm = re.sub(r"\s+", "", employee_id).strip().upper()

        # Step 1: Check if Employee ID exists
        id_match = df[df["EmployeeID_norm"] == empid_norm]
        if id_match.empty:
            return "❌ Employee ID not found. Please recheck it."

        # Step 2: Check Name + ID together
        match = id_match[id_match["Name_norm"] == name_norm]
        if match.empty:
            return "❌ Name and Employee ID don't match. Please try again."

        # Step 3: Extract record
        record = match.iloc[0]
        email = str(record["Email"]).strip()
        emp_name = record["Name"]

        # ---------------- Session Setup ----------------
        if email not in otp_sessions:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}

        # ---------------- OTP Handling ----------------
        if otp is None:  # User didn't provide OTP yet → Send/Resend
            generated_otp = str(random.randint(100000, 999999))
            otp_sessions[email]["otp"] = generated_otp
            otp_sessions[email]["verified"] = False
            otp_sessions[email]["attempts"] = 0
            otp_sessions[email]["name"] = emp_name
            otp_sessions[email]["employee_id"] = record["EmployeeID"]

            # Dev-mode: do not send email; reveal OTP in response for easy testing
            from .config import is_dev_mode_otp
            if is_dev_mode_otp():
                return (
                    f"✅ [DEV MODE] OTP generated for {emp_name}. "
                    f"Use this OTP to verify: {generated_otp}"
                )

            # Send OTP via Gmail (production)
            creds = get_gmail_credentials()
            if not creds['user'] or not creds['password']:
                return "❌ Email sending failed: Gmail credentials not configured."

            msg = MIMEMultipart()
            msg["From"] = creds['user']
            msg["To"] = email
            msg["Subject"] = "Your One-Time Password (OTP)"
            msg.attach(MIMEText(f"Hello {emp_name}, your OTP is: {generated_otp}", "plain"))

            try:
                server = smtplib.SMTP("smtp.gmail.com", 587)
                server.starttls()
                server.login(creds['user'], creds['password'])
                server.sendmail(creds['user'], [email], msg.as_string())
                server.quit()
            except Exception as e:
                return f"❌ Error sending OTP: {str(e)}"

            return f"✅ Hi {emp_name}, I sent an OTP to your email ({email}). Please tell me the OTP now."

        # ---------------- OTP Verification ----------------
        saved_otp = otp_sessions[email].get("otp")
        attempts = otp_sessions[email].get("attempts", 0)

        if attempts >= 3:
            otp_sessions[email] = {"otp": None, "verified": False, "attempts": 0}
            return "❌ Too many failed OTP attempts. Restart verification."

        if saved_otp and otp.strip() == saved_otp:
            otp_sessions[email]["verified"] = True

            # ✅ Manager Visit Greeting
            try:
                df_mgr = pd.read_csv(MANAGER_VISIT_CSV, dtype=str).fillna("")
                df_mgr["EmployeeID_norm"] = df_mgr["EmployeeID"].astype(str).str.strip().str.upper()
                df_mgr["Visit Date"] = pd.to_datetime(
                    df_mgr["Visit Date"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
                today = datetime.now().strftime("%Y-%m-%d")

                mgr_match = df_mgr[
                    (df_mgr["EmployeeID_norm"] == empid_norm)
                    & (df_mgr["Visit Date"] == today)
                ]

                if not mgr_match.empty:
                    office = mgr_match.iloc[0].get("Office", "our office")
                    manager = mgr_match.iloc[0].get("Manager Name", emp_name)
                    return (
                        f"✅ OTP verified. \n"
                        f" Welcome {emp_name}!, we're honored to have you visiting our {office} office today.\n"
                        f"Hope you had a smooth and comfortable journey.\n"
                        f"It was wonderful having you at our {office} office!\n"
                        f"We truly hope your visit was both memorable and meaningful.\n"
                        f"Thanks so much for taking the time to be with us—it really meant a lot to the whole {office} team."
                    )
            except FileNotFoundError:
                pass

            # Default success message
            return f"✅ OTP verified. Welcome {emp_name}! You now have full access to all tools."
        else:
            otp_sessions[email]["attempts"] = attempts + 1
            return f"❌ OTP incorrect. Attempts left: {3 - (attempts + 1)}."

    except FileNotFoundError:
        return "❌ Employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying employee: {str(e)}"