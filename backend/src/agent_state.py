import time
import json
import os
from datetime import datetime
from pathlib import Path

# -------------------- Global State Variables --------------------
is_awake = False  # Clara starts sleeping - only responds to 'Hey Clara'
wake_word = "hey clara"
sleep_phrase = "go idle"
last_activity = time.time()  # Track last interaction
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
    return "🤖 I'm awake! How can I help?"

def go_to_sleep():
    """Put Clara to sleep state"""
    global is_awake
    is_awake = False
    return "😴 Going idle, say 'Hey Clara' to wake me again."

def save_state_to_file():
    """Save current state to shared file"""
    state = {
        "is_awake": is_awake,
        "is_verified": is_verified,
        "verified_user_name": verified_user_name,
        "verified_user_id": verified_user_id,
        "last_activity": last_activity,
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
    global is_awake, is_verified, verified_user_name, verified_user_id, last_activity
    
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            
            is_awake = state.get("is_awake", True)
            is_verified = state.get("is_verified", False)
            verified_user_name = state.get("verified_user_name")
            verified_user_id = state.get("verified_user_id")
            last_activity = state.get("last_activity", time.time())
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
        return "💤 Clara has gone idle due to inactivity. Say 'Hey Clara' to wake me up."
    return None

def set_user_verified(name: str, user_id: str = None):
    """Mark user as verified with their details"""
    global is_verified, verified_user_name, verified_user_id
    is_verified = True
    verified_user_name = name
    verified_user_id = user_id
    update_activity()  # This now saves state to file
    print(f"✅ User verified: {name} (ID: {user_id})")
    
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
        "auto_sleep_in": max(0, AUTO_SLEEP_TIMEOUT - (time.time() - last_activity)) if is_awake else 0
    }

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
    
    user_input_lower = user_input.lower().strip()
    
    # Check for auto-sleep first
    auto_sleep_msg = check_auto_sleep()
    if auto_sleep_msg:
        return True, auto_sleep_msg
    
    # If Clara is sleeping
    if not is_awake:
        # Only respond to the exact wake phrase
        if wake_word == user_input_lower or wake_word in user_input_lower:
            response = wake_up()
            return True, response
        else:
            # Clara is asleep, ignore ALL other inputs (no response at all)
            return False, ""
    
    # Clara is awake - update activity
    update_activity()
    
    # Check for sleep command
    if sleep_phrase in user_input_lower:
        response = go_to_sleep()
        return True, response
    
    # Check for wake command (redundant but for completeness)
    if wake_word in user_input_lower:
        return True, "🤖 I'm already awake! How can I help you?"
    
    # Normal awake state - should respond to everything
    return True, ""