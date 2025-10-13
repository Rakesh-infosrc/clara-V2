import os
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ---------------- File Paths ----------------

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
COMPANY_INFO_PDF = str(DATA_DIR / "company_info.pdf")
VISITOR_LOG = str(DATA_DIR / "visitor_log.csv")
MANAGER_VISIT_CSV = str(DATA_DIR / "manager_visit.csv")
VISA_PDF_TEMPLATE = os.getenv("VISA_PDF_TEMPLATE")

# ---------------- AWS Configuration ----------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_REGION_ENV = os.getenv("AWS_REGION")
AWS_REGION = AWS_REGION_ENV or "us-east-1"
EMPLOYEE_TABLE_NAME = os.getenv("EMPLOYEE_TABLE_NAME", "zenith-hr-employees")
EMPLOYEE_EMAIL_INDEX = os.getenv("EMPLOYEE_EMAIL_INDEX", "EmailIndex")
EMPLOYEE_ID_INDEX = os.getenv("EMPLOYEE_ID_INDEX", "EmployeeIdIndex")
VISITOR_LOG_TABLE_NAME = os.getenv("VISITOR_LOG_TABLE_NAME", "Clara_visitor_log")
MANAGER_VISIT_TABLE_NAME = os.getenv("MANAGER_VISIT_TABLE_NAME", "Clara_manager_visits")
VISITOR_PHOTO_BUCKET = os.getenv("VISITOR_PHOTO_BUCKET")
VISITOR_PHOTO_PREFIX = os.getenv("VISITOR_PHOTO_PREFIX", "")
COMPANY_INFO_S3_BUCKET = os.getenv("COMPANY_INFO_S3_BUCKET")
COMPANY_INFO_S3_KEY = os.getenv("COMPANY_INFO_S3_KEY")
FACE_S3_BUCKET = os.getenv("FACE_S3_BUCKET")
FACE_IMAGE_BUCKET = os.getenv("FACE_IMAGE_BUCKET") or FACE_S3_BUCKET
FACE_ENCODING_S3_KEY = os.getenv("FACE_ENCODING_S3_KEY", "Pickle_file/encoding.pkl")
FACE_IMAGE_PREFIX = os.getenv("FACE_IMAGE_PREFIX", "Employee_Images")
FACE_IMAGE_EXTENSION = os.getenv("FACE_IMAGE_EXTENSION", "jpg")
FACE_RECOGNITION_ENABLED = os.getenv("FACE_RECOGNITION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TWILIO_DEFAULT_COUNTRY_CODE = os.getenv("TWILIO_DEFAULT_COUNTRY_CODE", "")

# ---------------- Global Variables ----------------
otp_sessions = defaultdict(dict)  # Track OTPs temporarily
# ---------------- Email Configuration ----------------


def get_gmail_user() -> str | None:
    """Return Gmail username used for SMTP delivery."""
    if not GMAIL_USER:
        return None
    user = GMAIL_USER.strip()
    return user or None


def get_gmail_app_password() -> str | None:
    """Return Gmail app password used for SMTP delivery."""
    if not GMAIL_APP_PASSWORD:
        return None
    password = GMAIL_APP_PASSWORD.strip().replace(" ", "")
    return password or None


def get_twilio_account_sid() -> str | None:
    """Return Twilio Account SID for SMS delivery."""
    return TWILIO_ACCOUNT_SID


def get_twilio_auth_token() -> str | None:
    """Return Twilio Auth Token for SMS delivery."""
    return TWILIO_AUTH_TOKEN


def get_twilio_phone_number() -> str | None:
    """Return Twilio phone number for SMS delivery."""
    return TWILIO_PHONE_NUMBER


def get_twilio_default_country_code() -> str | None:
    """Return default country code used when normalizing SMS phone numbers."""
    code = (TWILIO_DEFAULT_COUNTRY_CODE or "").strip()
    return code or None


def get_visitor_photo_bucket() -> str | None:
    """Return the configured S3 bucket for visitor photos, if any."""
    return VISITOR_PHOTO_BUCKET

def is_face_recognition_enabled() -> bool:
    """Return True when face recognition flow should auto-verify employees."""
    return FACE_RECOGNITION_ENABLED


def get_visitor_photo_prefix() -> str:
    """Return an optional root prefix for visitor photo S3 keys."""
    return VISITOR_PHOTO_PREFIX.strip("/")


def get_company_info_location() -> tuple[str | None, str | None]:
    """Return S3 bucket/key for company info PDF if configured."""
    return COMPANY_INFO_S3_BUCKET, COMPANY_INFO_S3_KEY

# ---------------- Dev Flags ----------------

def is_dev_mode_otp() -> bool:
    """When true, OTP emails are not sent; OTP is returned/logged for development."""
    val = os.getenv("DEV_MODE_OTP", "false").strip().lower()
    return val in {"1", "true", "yes", "on"}
