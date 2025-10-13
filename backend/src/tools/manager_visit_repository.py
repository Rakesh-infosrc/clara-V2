import boto3
from botocore.exceptions import ClientError
from datetime import datetime

from .config import AWS_REGION, MANAGER_VISIT_TABLE_NAME

_dynamodb = None
_table = None


def _get_table():
    global _dynamodb, _table
    if _table is not None:
        return _table

    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    _table = _dynamodb.Table(MANAGER_VISIT_TABLE_NAME)
    return _table


def get_manager_visit(employee_id: str, visit_date: str | None = None) -> dict | None:
    """Fetch manager visit details for the employee on the given date."""
    if not employee_id:
        return None

    normalized_id = employee_id.strip().upper()
    if not normalized_id:
        return None

    date_key = visit_date or datetime.now().strftime("%Y-%m-%d")
    table = _get_table()

    try:
        response = table.get_item(
            Key={
                "employee_id": normalized_id,
                "visit_date": date_key,
            }
        )
    except ClientError as exc:
        print(
            "[manager_visit_repository] get_item failed",
            {
                "employee_id": normalized_id,
                "visit_date": date_key,
                "error": str(exc),
            },
        )
        return None

    item = response.get("Item")
    if item:
        return item

    # Fallback: some tables may store mixed-case keys
    try:
        response = table.get_item(
            Key={
                "employee_id": employee_id,
                "visit_date": date_key,
            }
        )
    except ClientError:
        return None

    return response.get("Item")


def put_manager_visit(
    employee_id: str,
    visit_date: str | None = None,
    **attributes,
) -> bool:
    """Create or overwrite a manager visit record.

    Extra keyword arguments become additional DynamoDB attributes, e.g.
    ``manager_name="Priya", office="Chennai", notes="Quarterly review"``.
    """

    if not employee_id:
        return False

    normalized_id = employee_id.strip().upper()
    if not normalized_id:
        return False

    date_key = visit_date or datetime.now().strftime("%Y-%m-%d")
    item = {"employee_id": normalized_id, "visit_date": date_key}
    for key, value in attributes.items():
        if value is None:
            continue
        item[key] = value

    table = _get_table()

    try:
        table.put_item(Item=item)
    except ClientError as exc:
        print(
            "[manager_visit_repository] put_item failed",
            {"item": item, "error": str(exc)},
        )
        return False

    return True
