import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from .config import (
    AWS_REGION,
    EMPLOYEE_TABLE_NAME,
    EMPLOYEE_EMAIL_INDEX,
    EMPLOYEE_ID_INDEX,
    EMPLOYEE_PRIMARY_KEY,
)


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().replace(".", " ").split()).lower()


def _tokenize_name(value: str | None) -> set[str]:
    normalized = _normalize_name(value)
    if not normalized:
        return set()
    return {token for token in normalized.split(" ") if token}

_dynamodb = None
_table = None


def _get_table():
    global _dynamodb, _table
    if _table is not None:
        return _table

    _dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    _table = _dynamodb.Table(EMPLOYEE_TABLE_NAME)
    return _table


def _map_item(item: dict | None) -> dict | None:
    if not item:
        return None

    full_name = item.get("name")
    if not full_name:
        first = (item.get("first_name") or "").strip()
        last = (item.get("last_name") or "").strip()
        full_name = (f"{first} {last}").strip() or None

    return {
        "employee_id": item.get("employee_id") or item.get("id"),
        "name": full_name,
        "email": item.get("email"),
        "phone": item.get("phone") or item.get("mobile"),
        "department": item.get("department"),
        "photo_url": item.get("photo_url"),
        "raw": item,
    }


def get_employee_by_email(email: str) -> dict | None:
    """Fetch employee record from DynamoDB using the email GSI."""
    if not email:
        return None

    table = _get_table()

    candidates: list[str] = []
    raw_email = email.strip()
    if raw_email:
        candidates.append(raw_email)
    lowered = raw_email.lower()
    if lowered and lowered not in candidates:
        candidates.append(lowered)

    try:
        region = table.meta.client.meta.region_name
    except Exception:
        region = "unknown"
    print(
        "[employee_repository] DynamoDB email lookup",
        {
            "table": EMPLOYEE_TABLE_NAME,
            "index": EMPLOYEE_EMAIL_INDEX,
            "region": region,
            "candidates": candidates,
        },
    )

    items: list[dict] = []
    for candidate in candidates:
        try:
            response = table.query(
                IndexName=EMPLOYEE_EMAIL_INDEX,
                KeyConditionExpression=Key("email").eq(candidate),
                Limit=1,
            )
        except ClientError as exc:
            print(f"[employee_repository] DynamoDB query failed: {exc}")
            return None

        items = response.get("Items", [])
        print(
            "[employee_repository] Query attempt",
            {"candidate": candidate, "count": len(items)},
        )
        if items:
            break

    if not items:
        print(
            "[employee_repository] No exact-case items found for candidates",
            candidates,
        )

        lowered_target = lowered
        if lowered_target:
            scan_kwargs = {}
            while True:
                try:
                    response = table.scan(**scan_kwargs)
                except ClientError as exc:
                    print(f"[employee_repository] DynamoDB scan failed: {exc}")
                    break

                for item in response.get("Items", []):
                    email_value = (item.get("email") or "").strip()
                    if email_value and email_value.lower() == lowered_target:
                        print(
                            "[employee_repository] Scan fallback matched email",
                            {"stored": email_value, "requested": email},
                        )
                        items = [item]
                        break

                if items or "LastEvaluatedKey" not in response:
                    break

                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    if not items:
        print(
            "[employee_repository] No items found for candidates",
            candidates,
        )
        return None

    return _map_item(items[0])


def get_employee_by_id(employee_id: str) -> dict | None:
    """Fetch employee record from DynamoDB using the primary key."""
    if not employee_id:
        return None

    table = _get_table()
    key = employee_id.strip()
    if not key:
        return None

    print(
        "[employee_repository] DynamoDB id lookup",
        {
            "table": EMPLOYEE_TABLE_NAME,
            "region": table.meta.client.meta.region_name,
            "key": key,
        },
    )

    response = None

    try:
        response = table.get_item(Key={EMPLOYEE_PRIMARY_KEY: key})
    except ClientError as exc:
        print(f"[employee_repository] DynamoDB get_item failed: {exc}")

    item = response.get("Item") if response else None

    if not item and EMPLOYEE_ID_INDEX:
        try:
            response = table.query(
                IndexName=EMPLOYEE_ID_INDEX,
                KeyConditionExpression=Key("employee_id").eq(key),
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                item = items[0]
        except ClientError as exc:
            print(f"[employee_repository] DynamoDB id index query failed: {exc}")
            return None

    if not item:
        print(
            "[employee_repository] No item found for id",
            key,
        )
        return None

    return _map_item(item)


def get_employee_by_name(name: str) -> dict | None:
    """Fetch employee record by name using a case-insensitive scan."""
    if not name:
        return None

    table = _get_table()
    target = _normalize_name(name)
    if not target:
        return None

    target_tokens = _tokenize_name(name)
    scan_kwargs = {}
    print(
        "[employee_repository] DynamoDB name scan",
        {
            "table": EMPLOYEE_TABLE_NAME,
            "region": table.meta.client.meta.region_name,
            "target": target,
        },
    )

    while True:
        try:
            response = table.scan(**scan_kwargs)
        except ClientError as exc:
            print(f"[employee_repository] DynamoDB scan for name failed: {exc}")
            return None

        for item in response.get("Items", []):
            stored_name = _normalize_name(item.get("name") or item.get("full_name"))
            first = _normalize_name(item.get("first_name"))
            last = _normalize_name(item.get("last_name"))
            combined = " ".join(token for token in [first, last] if token).strip()
            stored_tokens = _tokenize_name(item.get("name"))
            stored_tokens.update(_tokenize_name(item.get("full_name")))
            stored_tokens.update(_tokenize_name(item.get("first_name")))
            stored_tokens.update(_tokenize_name(item.get("last_name")))

            match_exact = stored_name == target or combined == target
            match_tokens = target_tokens.issubset(stored_tokens) if target_tokens else False

            if match_exact or match_tokens:
                print(
                    "[employee_repository] Name scan matched",
                    {"stored": item.get("name"), "requested": name},
                )
                return _map_item(item)

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(
        "[employee_repository] No employee matched name",
        target,
    )
    return None
