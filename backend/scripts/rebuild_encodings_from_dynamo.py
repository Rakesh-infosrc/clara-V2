"""Rebuild face encodings from DynamoDB photo URLs and upload encoding.pkl to S3.

Run inside the backend virtualenv after exporting AWS credentials:

    python scripts/rebuild_encodings_from_dynamo.py

The script scans every employee record, downloads the `photo_url`,
extracts a face encoding, and saves the pickle via
`tools.face_recognition.save_face_encoding_data()` so it lands at the
configured `FACE_ENCODING_S3_KEY` (default: Pickle_file/encoding.pkl).
"""
from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from typing import Iterable

import requests
import face_recognition
import numpy as np
{{ ... }}

# Ensure backend/src is on sys.path so `tools` package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from tools.config import (
    EMPLOYEE_TABLE_NAME,
    FACE_ENCODING_S3_KEY,
    FACE_IMAGE_BUCKET,
    FACE_S3_BUCKET,
)
from tools.employee_repository import _get_table
from tools.face_recognition import save_face_encoding_data


@dataclass
class EmployeePhoto:
    employee_id: str
    photo_url: str


def iter_employee_photos() -> Iterable[EmployeePhoto]:
    """Yield `EmployeePhoto` records for every DynamoDB item with a photo URL."""

    table = _get_table()
    scan_kwargs: dict = {}

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            emp_id = (item.get("employee_id") or item.get("id") or "").strip()
            photo_url = (item.get("photo_url") or "").strip()
            if not emp_id or not photo_url:
                continue
            yield EmployeePhoto(employee_id=emp_id, photo_url=photo_url)

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]


def download_image(url: str) -> bytes:
    """Download image bytes from a (possibly signed) S3 URL."""

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def build_encodings() -> tuple[list[np.ndarray], list[str]]:
    encodings: list[np.ndarray] = []
    employee_ids: list[str] = []
    total = 0
    skipped = 0

    for photo in iter_employee_photos():
        total += 1
        try:
            print(f"[INFO] Fetching photo for {photo.employee_id}")
            image_bytes = download_image(photo.photo_url)
            image = face_recognition.load_image_file(io.BytesIO(image_bytes))
            vectors = face_recognition.face_encodings(image)
        except Exception as exc:  # noqa: BLE001 - we want to keep processing others
            skipped += 1
            print(f"[WARN] Failed to process {photo.employee_id}: {exc}")
            continue

        if not vectors:
            skipped += 1
            print(f"[WARN] No face detected for {photo.employee_id}")
            continue

        encodings.append(vectors[0])
        employee_ids.append(photo.employee_id)

    print(
        "[SUMMARY] Processed %d employees, built %d encodings, skipped %d"
        % (total, len(encodings), skipped)
    )

    return encodings, employee_ids


def main() -> int:
    source_bucket = FACE_IMAGE_BUCKET or FACE_S3_BUCKET or "(not set)"
    print(f"[CONFIG] DynamoDB table: {EMPLOYEE_TABLE_NAME}")
    print(f"[CONFIG] Encoding destination: {source_bucket}/{FACE_ENCODING_S3_KEY}")

    encodings, employee_ids = build_encodings()
    if not encodings:
        print("[ERROR] No encodings were generated; aborting upload.")
        return 1

    payload = {
        "encodings": encodings,
        "employee_ids": employee_ids,
    }

    if save_face_encoding_data(payload):
        print(
            "[SUCCESS] encoding.pkl saved to %s/%s"
            % (source_bucket, FACE_ENCODING_S3_KEY)
        )
        return 0

    print("[ERROR] Failed to upload encoding data")
    return 1


if __name__ == "__main__":
    sys.exit(main())
