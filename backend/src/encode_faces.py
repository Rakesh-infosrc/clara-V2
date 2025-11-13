import io
import pickle
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import time
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
    """Download an image from S3 with simple retries and return as numpy array."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = client.get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            return face_recognition.load_image_file(io.BytesIO(body))
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                # Backoff before retrying transient errors
                time.sleep(0.6 * (attempt + 1))
                continue
            raise


def _encode_image_robust(image):
    """Try multiple strategies to obtain a single face encoding from an image."""
    # 1) Default quick path
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0], None

    # 2) Fallbacks: increase upsample and use HOG model explicitly
    for upsample in (1, 2):
        locations = face_recognition.face_locations(
            image, number_of_times_to_upsample=upsample, model="hog"
        )
        if locations:
            encodings = face_recognition.face_encodings(
                image, known_face_locations=locations, num_jitters=2
            )
            if encodings:
                return encodings[0], None

    # 3) Optional CNN detector (if available), best-effort
    try:
        locations = face_recognition.face_locations(image, model="cnn")
        if locations:
            encodings = face_recognition.face_encodings(
                image, known_face_locations=locations, num_jitters=1
            )
            if encodings:
                return encodings[0], None
    except Exception:
        pass

    return None, "no_face"


def _encode_single_key(client, bucket: str, key: str) -> tuple[str | None, bytes | None, str]:
    try:
        image = _load_image_from_s3(client, bucket, key)
    except Exception as exc:  # pragma: no cover - defensive logging
        return None, None, f"  ⚠ Failed to load {key}: {exc}"

    encoding, _warn = _encode_image_robust(image)
    if encoding is None:
        return None, None, f"  ⚠ No face found in {key}"

    employee_id = Path(key).stem
    return employee_id, encoding, f"  ✔ Encoded Employee ID: {employee_id}"


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

    filtered_keys: list[str] = []
    seen_employee_ids: set[str] = set()
    key_order: dict[str, int] = {}

    for index, key in enumerate(sorted(image_keys)):
        suffix = Path(key).suffix.lower()
        if allowed_exts and suffix not in allowed_exts:
            continue
        employee_id = Path(key).stem
        if employee_id in seen_employee_ids:
            continue
        seen_employee_ids.add(employee_id)
        filtered_keys.append(key)
        key_order[key] = index

    if not filtered_keys:
        print("⚠️ No employee images with supported formats found in S3")
        return

    max_workers = min(8, len(filtered_keys)) or 1
    known_results: list[tuple[str, bytes]] = []
    failed_keys: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_encode_single_key, s3, image_bucket, key): key
            for key in filtered_keys
        }

        for future in as_completed(future_map):
            key = future_map[future]
            try:
                employee_id, encoding, message = future.result()
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"  ⚠ Unexpected error processing {key}: {exc}")
                continue

            if message:
                print(message)

            if employee_id and encoding is not None:
                known_results.append((employee_id, encoding))
            else:
                failed_keys.append(key)

    total = len(filtered_keys)
    print(f"[INFO] Encoded {len(known_results)}/{total} employees in this run")
    if failed_keys:
        print(f"[INFO] {len(failed_keys)} images had no detectable face or failed to load")
        for k in failed_keys[:10]:
            print(f"  ⚠ Skipped: {k}")

    if not known_results:
        print("⚠️ No face encodings were generated. Nothing to upload.")
        return

    known_results.sort(key=lambda item: item[0])
    known_ids = [employee_id for employee_id, _ in known_results]
    known_encodings = [encoding for _, encoding in known_results]

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
