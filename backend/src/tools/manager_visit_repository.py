import boto3
from botocore.exceptions import ClientError
from datetime import datetime

from .config import AWS_REGION, MANAGER_VISIT_TABLE_NAME


def _generate_date_candidates(date_key: str | None) -> list[str]:
    """Return possible DynamoDB date keys (both padded and non-padded)."""
    base_date = date_key or datetime.now().strftime("%Y-%m-%d")
    candidates = [base_date]

    try:
        parsed = datetime.strptime(base_date, "%Y-%m-%d")
    except ValueError:
        return candidates

    padded = parsed.strftime("%Y-%m-%d")
    non_padded = f"{parsed.year}-{parsed.month}-{parsed.day}"

    for variant in (padded, non_padded):
        if variant not in candidates:
            candidates.append(variant)

    return candidates

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

    table = _get_table()
    date_candidates = _generate_date_candidates(visit_date)
    employee_candidates = [value for value in {normalized_id: None, employee_id: None} if value]

    for date_key in date_candidates:
        for emp_key in employee_candidates:
            try:
                response = table.get_item(
                    Key={
                        "employee_id": emp_key,
                        "visit_date": date_key,
                    }
                )
            except ClientError as exc:
                print(
                    "[manager_visit_repository] get_item failed",
                    {
                        "employee_id": emp_key,
                        "visit_date": date_key,
                        "error": str(exc),
                    },
                )
                continue

            item = response.get("Item")
            if item:
                return item

    return None


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
