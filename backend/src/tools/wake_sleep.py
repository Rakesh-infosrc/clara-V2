import speech_recognition as sr
from livekit.agents import function_tool, RunContext
from agent_state import (
    is_awake, wake_word, sleep_phrase,
    wake_up, go_to_sleep, update_activity, check_auto_sleep
)


@function_tool()
async def listen_for_commands(context: RunContext) -> str:
    """Wake & Sleep Word Detection with inactivity timeout."""
    global is_awake
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("🎤 Listening for wake/sleep words...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, phrase_time_limit=5)

    try:
        text = r.recognize_google(audio).lower()

        # ⏳ Auto-sleep check
        auto_sleep_msg = check_auto_sleep()
        if auto_sleep_msg:
            return auto_sleep_msg

        if not is_awake:
            # Bot is sleeping → only wake phrase works
            if wake_word in text:
                return wake_up()
            # ❌ Don't print or echo random words when asleep
            return "🤫 Clara is sleeping. Ignoring input."

        # ✅ Reset timer (activity detected)
        update_activity()

        if sleep_phrase in text:
            return go_to_sleep()
        elif wake_word in text:
            return "Clara is already active."
        else:
            return f"Clara (active) heard: {text}"

    except sr.UnknownValueError:
        return "No recognizable speech detected."
    except Exception as e:
        return f"Error in wake/sleep detection: {e}"