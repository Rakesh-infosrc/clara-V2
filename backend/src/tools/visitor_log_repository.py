import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .config import AWS_REGION, VISITOR_LOG_TABLE_NAME

_dynamodb_resource: boto3.resources.base.ServiceResource | None = None


def _get_table():
    """Return the DynamoDB table resource for visitor logs."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", region_name=AWS_REGION)
    return _dynamodb_resource.Table(VISITOR_LOG_TABLE_NAME)


def put_visitor_log(
    visitor_name: str,
    phone: str,
    purpose: str,
    meeting_employee: str,
    photo_captured: bool,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Write a visitor entry into DynamoDB.

    Table schema (recommended):
      - Partition key:  `visit_date` (string, format YYYY-MM-DD)
      - Sort key:       `visit_id` (UUID string)
    """
    table = _get_table()
    visit_date = datetime.utcnow().strftime("%Y-%m-%d")
    visit_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    item: Dict[str, Any] = {
        "visit_date": visit_date,
        "visit_id": visit_id,
        "timestamp": timestamp,
        "visitor_name": visitor_name,
        "phone": phone,
        "purpose": purpose,
        "meeting_employee": meeting_employee,
        "photo_captured": photo_captured,
    }

    if metadata:
        item.update(metadata)

    try:
        table.put_item(Item=item)
        return item
    except ClientError as exc:
        print(f"[visitor_log_repository] DynamoDB put_item failed: {exc}")
        return None


def query_visitor_logs(
    date_filter: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Fetch visitor log entries, optionally filtered by visit date."""
    table = _get_table()

    try:
        if date_filter:
            response = table.query(
                KeyConditionExpression=Key("visit_date").eq(date_filter),
                ScanIndexForward=False,
                Limit=limit,
            )
            items = response.get("Items", [])
        else:
            # Fallback to scan when date is not specified; gather recent items.
            response = table.scan()
            items = response.get("Items", [])
            items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            items = items[:limit]
        return items
    except ClientError as exc:
        print(f"[visitor_log_repository] DynamoDB query/scan failed: {exc}")
        return []


def mark_photo_captured(visitor_name: str, visit_date: Optional[str] = None) -> bool:
    """Mark the most recent visitor entry for the visitor as having a captured photo."""
    target_date = visit_date or datetime.utcnow().strftime("%Y-%m-%d")
    records = query_visitor_logs(target_date, limit=25)

    normalized_target = visitor_name.strip().lower()
    latest = next(
        (
            item
            for item in sorted(
                records,
                key=lambda x: x.get("timestamp", ""),
                reverse=True,
            )
            if str(item.get("visitor_name", "")).strip().lower() == normalized_target
        ),
        None,
    )

    if not latest:
        return False

    table = _get_table()
    try:
        table.update_item(
            Key={
                "visit_date": latest["visit_date"],
                "visit_id": latest["visit_id"],
            },
            UpdateExpression="SET photo_captured = :val",
            ExpressionAttributeValues={":val": True},
        )
        latest["photo_captured"] = True
        return True
    except ClientError as exc:
        print(f"[visitor_log_repository] DynamoDB update_item failed: {exc}")
        return False
