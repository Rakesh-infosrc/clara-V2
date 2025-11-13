# Config Module

> Source: `src/tools/config.py`

## Purpose

Centralizes configuration for the backend tools by loading environment variables, preparing directory paths, and exposing helpers to access AWS, email, SMS, Graph, and face-recognition settings. Also lazily loads runtime feature flags like OTP dev mode.

## Key Functions

- `get_gmail_user()`, `get_gmail_app_password()`: Provide sanitized Gmail credentials for SMTP.
- `get_sns_*` helpers: Return AWS SNS configuration (region, sender ID, template IDs, etc.).
- `get_default_sms_country_code()`: Supplies the fallback country code for SMS normalization.
- `get_graph_*` helpers: Return Microsoft Graph client credentials and metadata.
- `get_company_info_location()`: Returns the S3 bucket/key for the company info PDF.
- `is_face_recognition_enabled()`, `is_dev_mode_otp()`: Feature flags controlling flow logic.
- Module-level constants such as `FACE_MATCH_TOLERANCE`, `FACE_S3_BUCKET`, `EMPLOYEE_TABLE_NAME` are consumed directly by other tools.

## Inputs

- Environment variables defined in `.env`, CloudFormation, or deployment platform. Examples: `FACE_S3_BUCKET`, `AWS_REGION`, `GMAIL_USER`, `GRAPH_CLIENT_ID`, `VISITOR_PHOTO_BUCKET`.

## Outputs

- Provides module-level constants and functions that other modules import to obtain consistent configuration values.

## Dependencies

- `dotenv` to load `.env`.
- `os`, `pathlib` for path resolution.
- `collections.defaultdict` for shared OTP session cache.

## Typical Usage

```python
from tools.config import FACE_S3_BUCKET, get_sns_sender_id
bucket = FACE_S3_BUCKET
sender_id = get_sns_sender_id()
```

## Error Handling & Edge Cases

- Wraps `FACE_MATCH_TOLERANCE` parsing in a `try/except` to fall back to a safe default.
- Directory paths (`data`, `config`, `logs`) are created if missing to avoid runtime `FileNotFoundError`s.

## Related Files

- All other tool modules import this file for configuration (e.g., `face_recognition`, `sms_sender`, `teams_sender`).
- `.env` or deployment-specific configuration templates must expose the expected environment variables.
