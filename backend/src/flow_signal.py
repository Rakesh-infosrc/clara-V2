"""
Simple in-memory signaling between the agent and the frontend.
Used to request client-side actions like starting/stopping face capture.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

# In-memory signal storage (works in single-process environment like ECS)
_current_signal: Optional[Dict[str, Any]] = None
_signal_timestamp: float = 0

# Fallback to file-based for development
SIGNAL_FILE = Path(__file__).parent.parent / "data" / "flow_signal.json"
SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)


def post_signal(name: str, payload: Optional[Dict[str, Any]] = None) -> None:
    """Post a single signal. Overwrites any existing pending signal."""
    global _current_signal, _signal_timestamp
    
    data = {
        "name": name,
        "payload": payload or {},
        "timestamp": time.time()
    }
    
    # Store in memory (primary method for ECS)
    _current_signal = data
    _signal_timestamp = time.time()
    
    # Also store in file (fallback for development)
    try:
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Warning: Could not write signal file: {e}")
    
    print(f"[SIGNAL] Posted: {name} with payload: {payload}")


def get_signal(clear: bool = True) -> Optional[Dict[str, Any]]:
    """Get the current signal. Optionally clear it afterwards."""
    global _current_signal, _signal_timestamp
    
    # Check in-memory first (primary method for ECS)
    if _current_signal is not None:
        signal = _current_signal.copy()
        if clear:
            _current_signal = None
            _signal_timestamp = 0
        print(f"[SIGNAL] Retrieved from memory: {signal.get('name')}")
        return signal
    
    # Fallback to file-based (for development)
    if not SIGNAL_FILE.exists():
        return None
    try:
        with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if clear:
            try:
                SIGNAL_FILE.unlink(missing_ok=True)
            except Exception:
                pass
        
        print(f"[SIGNAL] Retrieved from file: {data.get('name')}")
        return data
    except Exception:
        return None


def clear_signal() -> None:
    """Explicitly clear any pending signal."""
    global _current_signal, _signal_timestamp
    _current_signal = None
    _signal_timestamp = 0
    
    # Also clear file-based signal
    try:
        if SIGNAL_FILE.exists():
            SIGNAL_FILE.unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Could not clear signal file: {e}")
    
    print("[SIGNAL] Cleared all pending signals")


essential_actions = {
    "start_face_capture": "Ask the frontend to start face capture and send image to /flow/face_recognition",
    "start_visitor_photo": "Ask the frontend to start visitor photo capture and send image to /flow/visitor_photo",
    "stop_face_capture": "Ask the frontend to stop camera",
}
