import os
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# ---------------- File Paths ----------------
import os
from pathlib import Path

# Get the project root directory (backend folder)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "dummy-data"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# File paths using proper directory structure
ENCODING_FILE = str(DATA_DIR / "encoding.pkl")
EMPLOYEE_CSV = str(DATA_DIR / "employee_details.csv")
CANDIDATE_CSV = str(DATA_DIR / "candidate_interview.csv")
COMPANY_INFO_PDF = str(DATA_DIR / "company_info.pdf")
VISITOR_LOG = str(DATA_DIR / "visitor_log.csv")
MANAGER_VISIT_CSV = str(DATA_DIR / "manager_visit.csv")

# ---------------- Global Variables ----------------
otp_sessions = defaultdict(dict)  # Track OTPs temporarily

# ---------------- Gmail Configuration ----------------
def get_gmail_credentials():
    """Get Gmail credentials from environment variables"""
    return {
        'user': os.getenv("GMAIL_USER"),
        'password': os.getenv("GMAIL_APP_PASSWORD")
    }

def validate_gmail_credentials():
    """Validate Gmail credentials are configured"""
    creds = get_gmail_credentials()
    if not creds['user'] or not creds['password']:
        return False, "❌ Email sending failed: Gmail credentials not configured."
    return True, ""

# ---------------- Dev Flags ----------------

def is_dev_mode_otp() -> bool:
    """When true, OTP emails are not sent; OTP is returned/logged for development."""
    val = os.getenv("DEV_MODE_OTP", "false").strip().lower()
    return val in {"1", "true", "yes", "on"}
