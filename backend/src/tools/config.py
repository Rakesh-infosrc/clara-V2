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
EMPLOYEE_CSV = str(DATA_DIR / "employee_details.csv")
COMPANY_INFO_PDF = str(DATA_DIR / "company_info.pdf")
VISITOR_LOG = str(DATA_DIR / "visitor_log.csv")
MANAGER_VISIT_CSV = str(DATA_DIR / "manager_visit.csv")
VISA_PDF_TEMPLATE = os.getenv("VISA_PDF_TEMPLATE")

# ---------------- AWS Configuration ----------------
# AWS Chennai account (SNS-only). DynamoDB/S3 stay on the primary account.
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_ENV = os.getenv("AWS_REGION")

# Prefer dedicated Chennai SNS credentials when provided; otherwise reuse the primary AWS keys.
SNS_ACCESS_KEY_ID = os.getenv("CHE_AWS_ACCESS_KEY_ID") or AWS_ACCESS_KEY_ID
SNS_SECRET_ACCESS_KEY = os.getenv("CHE_AWS_SECRET_ACCESS_KEY") or AWS_SECRET_ACCESS_KEY
AWS_REGION = os.getenv("CHE_AWS_REGION") or AWS_REGION_ENV or "us-east-1"
AWS_SNS_SENDER_ID = os.getenv("AWS_SNS_SENDER_ID")
AWS_SNS_SMS_TYPE = os.getenv("AWS_SNS_SMS_TYPE", "Transactional")
SMS_DEFAULT_COUNTRY_CODE = os.getenv("CHE_SMS_DEFAULT_COUNTRY_CODE", os.getenv("SMS_DEFAULT_COUNTRY_CODE", ""))
AWS_SNS_ENTITY_ID = os.getenv("CHE_SNS_ENTITY_ID", os.getenv("AWS_SNS_ENTITY_ID"))
AWS_SNS_TEMPLATE_ID = os.getenv("CHE_SNS_TEMPLATE_ID", os.getenv("AWS_SNS_TEMPLATE_ID"))
EMPLOYEE_TABLE_NAME = os.getenv("EMPLOYEE_TABLE_NAME", "zenith-hr-employees")
EMPLOYEE_EMAIL_INDEX = os.getenv("EMPLOYEE_EMAIL_INDEX", "EmailIndex")
EMPLOYEE_ID_INDEX = os.getenv("EMPLOYEE_ID_INDEX", "EmployeeIdIndex")
EMPLOYEE_PRIMARY_KEY = os.getenv("EMPLOYEE_PRIMARY_KEY", "id")
ID_INDEX_NAME = os.getenv("ID_INDEX_NAME", "id-index")
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
FACE_ENCODING_TABLE_NAME = os.getenv("FACE_ENCODING_TABLE_NAME", "clara_face_encodings")
FACE_ENCODING_TABLE_KEY = os.getenv("FACE_ENCODING_TABLE_KEY", "FACE_ENCODINGS")
FACE_IMAGE_META_S3_KEY = os.getenv("FACE_IMAGE_META_S3_KEY", "Pickle_file/employee_images.pkl")
try:
    FACE_MATCH_TOLERANCE = float(os.getenv("FACE_MATCH_TOLERANCE", "0.6"))
except ValueError:
    print("[config] Invalid FACE_MATCH_TOLERANCE provided. Falling back to 0.6")
    FACE_MATCH_TOLERANCE = 0.6
FACE_RECOGNITION_ENABLED = os.getenv("FACE_RECOGNITION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID") or os.getenv("GRAPH_APPLICATION_ID")
GRAPH_CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET")
GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
GRAPH_APP_OBJECT_ID = os.getenv("GRAPH_APP_OBJECT_ID")
GRAPH_APP_DISPLAY_NAME = os.getenv("GRAPH_APP_DISPLAY_NAME") or "Clara Bot"

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


def get_aws_region() -> str:
    """Return the AWS region configured for backend services."""
    return AWS_REGION


def get_sns_sender_id() -> str | None:
    """Return AWS SNS Sender ID for SMS delivery, if configured."""
    value = (AWS_SNS_SENDER_ID or "").strip()
    return value or None


def get_sns_sms_type() -> str:
    """Return AWS SNS SMS type (Transactional or Promotional)."""
    value = (AWS_SNS_SMS_TYPE or "Transactional").strip()
    return value or "Transactional"


def get_sns_entity_id() -> str | None:
    value = (AWS_SNS_ENTITY_ID or "").strip()
    return value or None


def get_sns_template_id() -> str | None:
    value = (AWS_SNS_TEMPLATE_ID or "").strip()
    return value or None


def get_default_sms_country_code() -> str | None:
    """Return default country code used when normalizing SMS phone numbers."""
    code = (SMS_DEFAULT_COUNTRY_CODE or "").strip()
    return code or None


def get_sns_region() -> str:
    """Return region for SNS (prefers Chennai account)."""
    region = (os.getenv("CHE_AWS_REGION") or AWS_REGION).strip()
    return region or "us-east-1"


def get_sns_access_key_id() -> str | None:
    """Return access key id for SNS using Chennai account when available."""
    value = (SNS_ACCESS_KEY_ID or "").strip()
    return value or None


def get_sns_secret_access_key() -> str | None:
    """Return secret access key for SNS using Chennai account when available."""
    value = (SNS_SECRET_ACCESS_KEY or "").strip()
    return value or None


def get_graph_client_id() -> str | None:
    return (GRAPH_CLIENT_ID or "").strip() or None


def get_graph_client_secret() -> str | None:
    return (GRAPH_CLIENT_SECRET or "").strip() or None


def get_graph_tenant_id() -> str | None:
    return (GRAPH_TENANT_ID or "").strip() or None


def get_graph_app_object_id() -> str | None:
    return (GRAPH_APP_OBJECT_ID or "").strip() or None


def get_graph_app_display_name() -> str:
    value = GRAPH_APP_DISPLAY_NAME or "Clara Bot"
    return value.strip() or "Clara Bot"


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
