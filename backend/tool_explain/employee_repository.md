# Employee Repository

> Source: `src/tools/employee_repository.py`

## Purpose

Provides read-only access to the employee DynamoDB table. Supports lookups by email, employee ID, and fuzzy name matching so that downstream tools can fetch contact information, phone numbers, and other metadata.

## Key Functions

- `_get_table()`: Lazily initializes the DynamoDB table resource using region/table names from `config.py`.
- `_map_item(item)`: Normalizes DynamoDB items into a consistent dictionary (`employee_id`, `name`, `email`, `phone`, etc.).
- `get_employee_by_email(email)`: Queries the GSI (`EMPLOYEE_EMAIL_INDEX`) for the provided email, falling back to scans for case-insensitive matches.
- `get_employee_by_id(employee_id)`: Retrieves employees via primary key or the `EMPLOYEE_ID_INDEX` secondary index.
- `get_employee_by_name(name)`: Performs a scan and token-based comparison to find employees by name regardless of ordering or punctuation.

## Inputs

- `email`, `employee_id`, or `name` strings supplied by other tools.
- AWS credentials and table/index names defined in environment variables.

## Outputs

- Returns a normalized employee dictionary when a match is found, otherwise `None`.
- Helper functions print diagnostic details to aid debugging but do not raise exceptions for missing records.

## Dependencies

- `boto3` DynamoDB resource.
- Configuration from `config.py`: `EMPLOYEE_TABLE_NAME`, `EMPLOYEE_EMAIL_INDEX`, `EMPLOYEE_ID_INDEX`, `AWS_REGION`, `EMPLOYEE_PRIMARY_KEY`.

## Typical Usage

```python
from tools.employee_repository import get_employee_by_id
employee = get_employee_by_id("EMP123")
if employee:
    phone = employee["phone"]
```

## Error Handling & Edge Cases

- Catches `ClientError` during queries/scans and logs messages, returning `None` so callers can handle fallbacks.
- Performs input sanitation (strip, lowercase) before querying.
- For name searches, tokenizes names to account for extra whitespace, punctuation, or differing order.

## Related Files

- `employee_verification.py`, `visitor_management.py`, `face_recognition.py` consume this module to fetch employee contact details.
- `config.py` supplies the table/index names and AWS region.
