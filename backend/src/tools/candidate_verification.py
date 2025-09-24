import re
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from livekit.agents import function_tool, RunContext
from .config import CANDIDATE_CSV, EMPLOYEE_CSV, otp_sessions, get_gmail_credentials


@function_tool()
async def get_candidate_details(
    context: RunContext, candidate_name: str, interview_code: str
) -> str:
    """
    Candidate verification tool (code-first approach):
    - Look up candidate by Interview Code (unique key).
    - Then cross-check the provided name.
    - Retry limit (max 3 attempts).
    - Notify interviewer via email if valid.
    """
    try:
        # Load candidate CSV as text (avoid dtype issues)
        df_candidates = pd.read_csv(CANDIDATE_CSV, dtype=str).fillna("")

        # Normalize interview codes in CSV
        df_candidates["InterviewCode_norm"] = (
            df_candidates["Interview Code"]
            .astype(str)
            .str.encode("ascii", "ignore")
            .str.decode("ascii")
            .str.strip()
            .str.replace(r"[^0-9A-Za-z]", "", regex=True)
            .str.upper()
        )

        # Normalize candidate names in CSV
        df_candidates["Candidate_norm"] = (
            df_candidates["Candidate Name"]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.lower()
        )

        # Normalize user inputs
        code_norm = (
            interview_code.encode("ascii", "ignore").decode("ascii").strip().upper()
        )
        cand_name_norm = (
            candidate_name.encode("ascii", "ignore").decode("ascii").strip().lower()
        )

        # Step 1: Lookup by code
        record_match = df_candidates[df_candidates["InterviewCode_norm"] == code_norm]
        if record_match.empty:
            return f"❌ Interview code '{interview_code}' not found in today's list."

        record = record_match.iloc[0]
        expected_name = record["Candidate_norm"]

        # Step 2: Verify name matches the code
        if cand_name_norm != expected_name:
            return (
                f"❌ The name '{candidate_name}' does not match our records "
                f"for interview code {interview_code}. Please recheck."
            )

        # Step 3: Retry memory for candidates
        session_key = code_norm
        if session_key not in otp_sessions:
            otp_sessions[session_key] = {"verified": False, "attempts": 0}

        attempts = otp_sessions[session_key].get("attempts", 0)
        if attempts >= 3:
            otp_sessions.pop(session_key, None)
            return "❌ Too many failed attempts. Please restart candidate verification."

        # Step 4: Notify interviewer
        interviewer_name = str(record["Interviewer"]).strip()
        cand_role = record["Interview Role"]
        cand_time = record["Interview Time"]

        # Load employees to get interviewer email
        df_employees = pd.read_csv(EMPLOYEE_CSV, dtype=str).fillna("")
        df_employees["Name_norm"] = (
            df_employees["Name"].astype(str).str.strip().str.lower()
        )

        interviewer = df_employees[
            df_employees["Name_norm"] == interviewer_name.strip().lower()
        ]
        if interviewer.empty:
            return f"❌ Interviewer '{interviewer_name}' not found in employee records."

        interviewer_email = interviewer.iloc[0]["Email"]

        # Gmail credentials
        creds = get_gmail_credentials()
        if not creds['user'] or not creds['password']:
            return "❌ Email sending failed: Gmail credentials not configured."

        # Prepare email
        msg = MIMEMultipart()
        msg["From"] = creds['user']
        msg["To"] = interviewer_email
        msg["Subject"] = f"Candidate {record['Candidate Name']} has arrived for interview"

        body = (
            f"Hi {interviewer_name},\n\n"
            f"Candidate {record['Candidate Name']} has arrived for the {cand_role} interview.\n\n"
            f"Interview Time: {cand_time}\n"
            f"Interview Code: {record['Interview Code']}\n\n"
            "Please let me know if you're ready to meet them."
        )
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(creds['user'], creds['password'])
            server.sendmail(creds['user'], [interviewer_email], msg.as_string())
            server.quit()
        except Exception as e:
            return f"❌ Error sending email to interviewer: {str(e)}"

        otp_sessions[session_key]["verified"] = True
        return (
            f"✅ Hello {record['Candidate Name']}, your interview for {cand_role} is scheduled at {cand_time}. "
            f"Please wait for a few moments, {interviewer_name} will meet you shortly."
        )

    except FileNotFoundError:
        return "❌ Candidate or employee database file is missing."
    except Exception as e:
        return f"❌ Error verifying candidate: {str(e)}"