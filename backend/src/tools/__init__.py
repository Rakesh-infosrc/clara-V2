# Import all tools for easy access
from .company_info import company_info
from .employee_verification import get_employee_details
from .visitor_management import log_and_notify_visitor, capture_visitor_photo, get_visitor_log, mark_visitor_photo_captured
try:
    # Optional: relies on speech_recognition; guard to avoid import errors when not installed
    from .wake_sleep import listen_for_commands
except Exception:
    listen_for_commands = None
from .weather import get_weather
from .web_search import search_web
from .email_sender import send_email
from .face_recognition import face_verify, face_login, run_face_verify
from .face_registration import register_employee_face, check_face_registration_status, remove_face_registration

# Make all tools available when importing from tools
__all__ = [
    'company_info',
    'get_employee_details', 
    'log_and_notify_visitor',
    'capture_visitor_photo',
    'get_visitor_log',
    'mark_visitor_photo_captured',
    'listen_for_commands',
    'get_weather',
    'search_web', 
    'send_email',
    'face_verify',
    'face_login',
    'run_face_verify',
    'register_employee_face',
    'check_face_registration_status',
    'remove_face_registration'
]
