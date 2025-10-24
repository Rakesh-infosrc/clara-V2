"""Utility script to send a test SMS via AWS SNS using the Clara configuration."""
import argparse
import os
import sys
from pathlib import Path

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Ensure project root (.env) loads before importing config-dependent modules
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
_load_env_file(PROJECT_ROOT / ".env")

try:
    from src.tools.sms_sender import send_sms_via_sns
except Exception as exc:  # pragma: no cover - basic guard for missing deps
    print(f"Failed to import send_sms_via_sns: {exc}")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test SMS using AWS SNS.")
    parser.add_argument("phone", help="Destination phone number (with or without country code)")
    parser.add_argument(
        "message",
        nargs="?",
        default="Clara SNS test message.",
        help="Message body to send. Defaults to 'Clara SNS test message.'",
    )
    parser.add_argument(
        "--sender-id",
        dest="sender_id",
        default=None,
        help="Optional sender ID override.",
    )
    parser.add_argument(
        "--sms-type",
        dest="sms_type",
        choices=["Transactional", "Promotional"],
        default=None,
        help="Optional SMS type override.",
    )
    parser.add_argument(
        "--region",
        dest="region",
        default=None,
        help="Override AWS region (defaults to Chennai account region if configured).",
    )
    parser.add_argument(
        "--access-key",
        dest="access_key",
        default=None,
        help="Optional AWS access key ID override for local testing.",
    )
    parser.add_argument(
        "--secret-key",
        dest="secret_key",
        default=None,
        help="Optional AWS secret access key override for local testing.",
    )

    args = parser.parse_args()

    try:
        result = send_sms_via_sns(
            to_phone=args.phone,
            message=args.message,
            sender_id=args.sender_id,
            sms_type=args.sms_type,
            region_override=args.region,
            access_key_override=args.access_key,
            secret_key_override=args.secret_key,
        )
    except Exception as exc:  # pragma: no cover - CLI feedback
        print(f"SNS send failed: {exc}")
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
