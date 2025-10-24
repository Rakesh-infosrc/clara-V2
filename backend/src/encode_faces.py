import io
import pickle
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
import face_recognition

from tools.config import (
    FACE_IMAGE_BUCKET,
    FACE_S3_BUCKET,
    FACE_IMAGE_PREFIX,
    FACE_IMAGE_EXTENSION,
    FACE_ENCODING_S3_KEY,
)

def _get_s3_client():
    return boto3.client("s3")


def _list_employee_images(client, bucket: str, prefix: str | None) -> list[str]:
    paginator = client.get_paginator("list_objects_v2")
    kwargs = {"Bucket": bucket}
    if prefix:
        kwargs["Prefix"] = prefix

    keys: list[str] = []
    for page in paginator.paginate(**kwargs):
        contents = page.get("Contents", [])
        for entry in contents:
            key = entry.get("Key")
            if not key or key.endswith("/"):
                continue
            keys.append(key)
    return keys


def _load_image_from_s3(client, bucket: str, key: str):
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    return face_recognition.load_image_file(io.BytesIO(body))


def main():
    image_bucket = FACE_IMAGE_BUCKET or FACE_S3_BUCKET
    if not image_bucket:
        print("❌ FACE_IMAGE_BUCKET or FACE_S3_BUCKET must be configured")
        return

    image_prefix = (FACE_IMAGE_PREFIX or "").strip("/")
    allowed_exts = {f".{FACE_IMAGE_EXTENSION.lower()}"} if FACE_IMAGE_EXTENSION else set()
    allowed_exts.update({".jpg", ".jpeg", ".png", ".webp"})

    s3 = _get_s3_client()

    print(f"[INFO] Listing employee images from s3://{image_bucket}/{image_prefix}")
    try:
        image_keys = _list_employee_images(s3, image_bucket, image_prefix or None)
    except (BotoCoreError, ClientError, NoCredentialsError) as exc:
        print(f"❌ Failed to list employee images from S3: {exc}")
        return

    if not image_keys:
        print("⚠️ No employee images found in S3")
        return

    known_encodings: list = []
    known_ids: list[str] = []

    for key in sorted(image_keys):
        suffix = Path(key).suffix.lower()
        if allowed_exts and suffix not in allowed_exts:
            continue

        try:
            image = _load_image_from_s3(s3, image_bucket, key)
        except Exception as exc:
            print(f"  ⚠ Failed to load {key}: {exc}")
            continue

        encodings = face_recognition.face_encodings(image)
        if not encodings:
            print(f"  ⚠ No face found in {key}")
            continue

        encoding = encodings[0]
        known_encodings.append(encoding)
        employee_id = Path(key).stem
        known_ids.append(employee_id)
        print(f"  ✔ Encoded Employee ID: {employee_id}")

    if not known_encodings:
        print("⚠️ No face encodings were generated. Nothing to upload.")
        return

    data = {"encodings": known_encodings, "employee_ids": known_ids}
    payload = pickle.dumps(data)

    encoding_bucket = FACE_S3_BUCKET or FACE_IMAGE_BUCKET
    encoding_key = FACE_ENCODING_S3_KEY

    if encoding_bucket and encoding_key:
        try:
            s3.put_object(
                Bucket=encoding_bucket,
                Key=encoding_key,
                Body=payload,
                ContentType="application/octet-stream",
            )
            print(f"[INFO] Face encodings saved to s3://{encoding_bucket}/{encoding_key}")
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            print(f"❌ Failed to upload face encodings to S3: {exc}")
    else:
        print("✔ FACE_S3_BUCKET/FACE_IMAGE_BUCKET or FACE_ENCODING_S3_KEY not configured; skipping S3 upload")


if __name__ == "__main__":
    main()
