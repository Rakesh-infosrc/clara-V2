"""
Simple file-based signaling between the agent and the frontend.
Used to request client-side actions like starting/stopping face capture.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Location to store signals
SIGNAL_FILE = Path(__file__).parent.parent / "data" / "flow_signal.json"
SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)


def post_signal(name: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Post a single signal. Overwrites any existing pending signal."""
    data = {
        "name": name,
        "payload": payload or {},
    }
    with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def get_signal(clear: bool = True) -> Optional[Dict[str, Any]]:
    """Get the current signal. Optionally clear it afterwards."""
    if not SIGNAL_FILE.exists():
        return None
    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if clear:
        try:
            SIGNAL_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    return data


essential_actions = {
    "start_face_capture": "Ask the frontend to start face capture and send image to /flow/face_recognition",
    "start_visitor_photo": "Ask the frontend to start visitor photo capture and send image to /flow/visitor_photo",
    "stop_face_capture": "Ask the frontend to stop camera",
}
