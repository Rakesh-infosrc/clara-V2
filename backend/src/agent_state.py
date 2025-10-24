import time
import json
import os
from datetime import datetime
from pathlib import Path

from language_utils import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    resolve_language_code,
    normalize_transcript,
    get_message,
    get_wake_phrases,
    get_sleep_phrases,
    any_phrase_in_text,
)

# -------------------- Global State Variables --------------------
is_awake = False  # Clara starts sleeping - only responds to 'Hey Clara'
wake_word = "hey clara"  # English fallback for external integrations
sleep_phrase = "go idle"
last_activity = time.time()  # Track last interaction
preferred_language = DEFAULT_LANGUAGE
AUTO_SLEEP_TIMEOUT = 180  # 3 minutes of inactivity = auto sleep

# -------------------- Shared State File --------------------
STATE_FILE = Path(__file__).parent.parent / "data" / "agent_state.json"

# -------------------- Verification State --------------------
is_verified = False  # Track if user is verified (face or manual)
verified_user_name = None  # Store verified user's name
verified_user_id = None  # Store verified user's employee ID

def wake_up():
    """Wake up Clara from sleep state"""
    global is_awake, last_activity
    is_awake = True
    last_activity = time.time()
    return get_message("wake_ack", get_preferred_language())

def go_to_sleep():
    """Put Clara to sleep state"""
    global is_awake
    is_awake = False
    return get_message("sleep_ack", get_preferred_language())

def save_state_to_file():
    """Save current state to shared file"""
    state = {
        "is_awake": is_awake,
        "is_verified": is_verified,
        "verified_user_name": verified_user_name,
        "verified_user_id": verified_user_id,
        "last_activity": last_activity,
        "preferred_language": preferred_language,
        "timestamp": time.time()
    }
    
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state_from_file():
    """Load state from shared file"""
    global is_awake, is_verified, verified_user_name, verified_user_id, last_activity, preferred_language
    
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            
            is_awake = state.get("is_awake", True)
            is_verified = state.get("is_verified", False)
            verified_user_name = state.get("verified_user_name")
            verified_user_id = state.get("verified_user_id")
            last_activity = state.get("last_activity", time.time())
            preferred_language = resolve_language_code(state.get("preferred_language", DEFAULT_LANGUAGE))
    except Exception as e:
        print(f"Error loading state: {e}")

def update_activity():
    """Update the last activity timestamp"""
    global last_activity
    last_activity = time.time()
    save_state_to_file()

def check_auto_sleep():
    """Check if Clara should auto-sleep due to inactivity"""
    global is_awake, last_activity
    if is_awake and (time.time() - last_activity) > AUTO_SLEEP_TIMEOUT:
        is_awake = False
        return get_message("auto_sleep_notice", get_preferred_language())
    return None

def set_user_verified(name: str, user_id: str = None):
    """Mark user as verified with their details"""
    global is_verified, verified_user_name, verified_user_id
    is_verified = True
    verified_user_name = name
    verified_user_id = user_id
    update_activity()  # This now saves state to file
    print(f" User verified: {name} (ID: {user_id})")
    
def clear_verification():
    """Clear verification status"""
    global is_verified, verified_user_name, verified_user_id
    is_verified = False
    verified_user_name = None
    verified_user_id = None
    save_state_to_file()

def get_state():
    """Get current state information"""
    return {
        "is_awake": is_awake,
        "is_verified": is_verified,
        "verified_user_name": verified_user_name,
        "verified_user_id": verified_user_id,
        "last_activity": datetime.fromtimestamp(last_activity).strftime("%Y-%m-%d %H:%M:%S"),
        "preferred_language": preferred_language,
        "auto_sleep_in": max(0, AUTO_SLEEP_TIMEOUT - (time.time() - last_activity)) if is_awake else 0
    }

def get_preferred_language() -> str:
    return preferred_language or DEFAULT_LANGUAGE


def set_preferred_language(lang_label: str) -> None:
    global preferred_language
    preferred_language = resolve_language_code(lang_label)
    save_state_to_file()


def _detect_language_by_script(text: str) -> str | None:
    """Detect language by Unicode script blocks.

    Returns a language code if a strong script signal is found, else None.
    - Tamil:    U+0B80–U+0BFF
    - Telugu:   U+0C00–U+0C7F
    - Devanagari (Hindi): U+0900–U+097F
    """
    for ch in text:
        cp = ord(ch)
        # Devanagari (Hindi)
        if 0x0900 <= cp <= 0x097F:
            return "hi"
        # Tamil
        if 0x0B80 <= cp <= 0x0BFF:
            return "ta"
        # Telugu
        if 0x0C00 <= cp <= 0x0C7F:
            return "te"
    return None


def _infer_language_from_input(user_input: str) -> str:
    text = user_input.strip()
    # 1) Strong signal: unicode script detection
    script_lang = _detect_language_by_script(text)
    if script_lang in SUPPORTED_LANGUAGES:
        return script_lang

    # 2) Fallback to phrase-based detection using normalized lower text
    text_lower = text.lower()
    for candidate in SUPPORTED_LANGUAGES:
        normalized = normalize_transcript(text_lower, candidate)
        wake_phrases = get_wake_phrases(candidate)
        sleep_phrases = get_sleep_phrases(candidate)
        if any_phrase_in_text(normalized, wake_phrases) or any_phrase_in_text(normalized, sleep_phrases):
            return candidate
    return get_preferred_language()

def _detect_language_switch_request(text: str) -> str | None:
    lowered = text.lower()
    patterns = {
        "ta": ["talk in tamil", "speak tamil", "tamil la", "tamil lo"],
        "te": ["talk in telugu", "speak telugu", "telugu lo", "telugu please"],
        "hi": ["talk in hindi", "speak hindi", "hindi mein", "hindi please"],
        "en": ["talk in english", "speak english", "english please"],
    }
    for lang_code, triggers in patterns.items():
        for phrase in triggers:
            if phrase in lowered:
                return lang_code
    stripped = text.strip()
    if len(stripped) >= 4 and (" " in stripped or "-" in stripped):
        detected = resolve_language_code(stripped.lower())
        if detected != DEFAULT_LANGUAGE:
            return detected
    return None


def process_input(user_input: str) -> tuple[bool, str]:
    """
    Process user input and return (should_respond, response)
    
    Args:
        user_input: The user's input text
        
    Returns:
        tuple: (should_respond: bool, response: str)
               - should_respond: Whether Clara should respond to this input
               - response: The response message (if any)
    """
    global is_awake
    
    switch_lang = _detect_language_switch_request(user_input)
    if switch_lang:
        set_preferred_language(switch_lang)
        lang = get_preferred_language()
        update_activity()
        return True, get_message("language_support_affirm", lang)

    detected_lang = _infer_language_from_input(user_input)
    if detected_lang != get_preferred_language():
        set_preferred_language(detected_lang)

    lang = get_preferred_language()
    normalized_input = normalize_transcript(user_input.strip(), lang)
    wake_phrases = get_wake_phrases(lang)
    sleep_phrases = get_sleep_phrases(lang)

    # Check for auto-sleep first
    auto_sleep_msg = check_auto_sleep()
    if auto_sleep_msg:
        return True, auto_sleep_msg

    # If Clara is sleeping
    if not is_awake:
        # Only respond to the exact wake phrase
        if any_phrase_in_text(normalized_input, wake_phrases):
            response = wake_up()
            return True, response
        else:
            # Clara is asleep, ignore ALL other inputs (no response at all)
            return False, ""

    # Clara is awake - update activity
    update_activity()

    # Check for sleep command
    if any_phrase_in_text(normalized_input, sleep_phrases):
        response = go_to_sleep()
        return True, response

    # Check for wake command (redundant but for completeness)
    if any_phrase_in_text(normalized_input, wake_phrases):
        return True, get_message("already_awake", lang)
    
    # Normal awake state - should respond to everything
    return True, ""