import pickle
from pathlib import Path
from urllib.parse import urlparse

import requests

import boto3
from botocore.exceptions import BotoCoreError, ClientError 

try:
    from .config import (
        AWS_REGION,
        EMPLOYEE_TABLE_NAME,
        FACE_S3_BUCKET,
        FACE_IMAGE_BUCKET,
        FACE_IMAGE_PREFIX,
        FACE_IMAGE_EXTENSION,
        FACE_ENCODING_S3_KEY,
    )
except ImportError:
    import importlib.util

    _config_path = Path(__file__).resolve().with_name("config.py")
    _spec = importlib.util.spec_from_file_location("tools_config", _config_path)
    if _spec is None or _spec.loader is None:
        raise
    _config = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_config)
    AWS_REGION = _config.AWS_REGION
    EMPLOYEE_TABLE_NAME = _config.EMPLOYEE_TABLE_NAME
    FACE_S3_BUCKET = _config.FACE_S3_BUCKET
    FACE_IMAGE_BUCKET = _config.FACE_IMAGE_BUCKET
    FACE_IMAGE_PREFIX = _config.FACE_IMAGE_PREFIX
    FACE_IMAGE_EXTENSION = _config.FACE_IMAGE_EXTENSION
    FACE_ENCODING_S3_KEY = _config.FACE_ENCODING_S3_KEY


def _image_bucket() -> str | None:
    return FACE_IMAGE_BUCKET or FACE_S3_BUCKET


def _encoding_bucket() -> str | None:
    return FACE_S3_BUCKET or FACE_IMAGE_BUCKET


def _image_prefix() -> str:
    return (FACE_IMAGE_PREFIX or "").strip("/")


def _guess_extension(photo_url: str) -> str:
    suffix = Path(urlparse(photo_url).path or "").suffix.lstrip(".")
    if suffix:
        return suffix.lower()
    fallback = (FACE_IMAGE_EXTENSION or "jpg").lstrip(".").lower()
    return fallback or "jpg"


def _content_type_for_extension(extension: str) -> str:
    ext = extension.lower()
    if ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"


def fetch_employee_images() -> dict[str, dict[str, str]]:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(EMPLOYEE_TABLE_NAME)
    scan_kwargs: dict = {}
    result: dict[str, dict[str, str]] = {}
    total_scanned = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        total_scanned += len(items)
        for item in items:
            photo_url_raw = (item.get("photo_url") or "").strip()
            if not photo_url_raw:
                continue
            employee_id = str(item.get("employee_id") or item.get("id") or "").strip()
            if not employee_id:
                continue
            name = (item.get("name") or "").strip()
            result[employee_id] = {"name": name, "photo_url": photo_url_raw}
            display_name = name or employee_id
            print(f"Employee processed: {display_name} -> {photo_url_raw}")
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"Total employees scanned: {total_scanned}")
    print(f"Employees with images: {len(result)}")
    return result


def upload_employee_images_pickle(data: dict[str, dict[str, str]]) -> bool:
    bucket = _encoding_bucket()
    key = FACE_ENCODING_S3_KEY

    if not bucket or not key:
        print("Missing S3 bucket or key configuration for face encodings.")
        return False

    s3_client = boto3.client("s3", region_name=AWS_REGION)
    payload = pickle.dumps(data)

    try:
        s3_client.put_object(Bucket=bucket, Key=key, Body=payload)
        print(f"Uploaded pickle to s3://{bucket}/{key}")
        return True
    except (BotoCoreError, ClientError) as exc:
        print(f"Failed to upload employee image pickle to S3: {exc}")
        return False


def main() -> None:
    try:
        data = fetch_employee_images()
    except (BotoCoreError, ClientError) as exc:
        print(f"Failed to fetch employee images: {exc}")
        return

    if not data:
        print("No employee images found.")
        return

    bucket = _image_bucket()
    prefix = _image_prefix()
    s3_client = boto3.client("s3", region_name=AWS_REGION)

    if not bucket:
        print("Missing S3 bucket configuration for employee images.")
        return

    uploaded: dict[str, str] = {}
    for employee_id, info in data.items():
        photo_url = info.get("photo_url")
        if not photo_url:
            continue

        try:
            response = requests.get(photo_url, timeout=15)
            response.raise_for_status()
        except Exception as exc:
            print(f"Failed to download image for {employee_id}: {exc}")
            continue

        ext = _guess_extension(photo_url)
        key_parts = [segment for segment in [prefix, f"{employee_id}.{ext}"] if segment]
        new_key = "/".join(key_parts)
        content_type = _content_type_for_extension(ext)

        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=new_key,
                Body=response.content,
                ContentType=content_type,
            )
            uploaded[employee_id] = new_key
            print(f"Uploaded S3 image for {employee_id} -> {new_key}")
        except (BotoCoreError, ClientError) as exc:
            print(f"Failed to upload image for {employee_id}: {exc}")

    if not uploaded:
        print("No images were uploaded; skipping pickle update.")
        return

    pickle_payload = {
        emp_id: {"name": data[emp_id]["name"], "photo_key": uploaded[emp_id]}
        for emp_id in uploaded
    }

    if upload_employee_images_pickle(pickle_payload):
        print(f"Uploaded {len(pickle_payload)} employee images to configured S3 location.")


if __name__ == "__main__":
    main()
