import os
from pathlib import Path
from typing import Optional

import speech_recognition as sr
from livekit.agents import function_tool, RunContext

from agent_state import (
    is_awake,
    wake_word,
    sleep_phrase,
    wake_up,
    go_to_sleep,
    update_activity,
    check_auto_sleep,
    set_preferred_language,
)
from speech import get_asr_instance
from language_utils import resolve_language_code

try:  # Optional dependency for language identification
    from fasttext import load_model  # type: ignore
except Exception:  # pragma: no cover - fasttext optional
    load_model = None  # type: ignore


_LID_MODEL: Optional[object] = None
_DEFAULT_LID_PATH = (Path(__file__).resolve().parents[1] / "Language_model" / "lid.176.ftz").as_posix()


def _load_language_identifier() -> Optional[object]:
    global _LID_MODEL
    if _LID_MODEL is not None:
        return _LID_MODEL
    try:
        model_path = os.getenv("FASTTEXT_MODEL_PATH", _DEFAULT_LID_PATH)
        _LID_MODEL = load_model(model_path)
    except Exception:
        _LID_MODEL = None
    return _LID_MODEL


def _detect_language(text: str) -> Optional[str]:
    model = _load_language_identifier()
    if not model:
        return None
    label, _prob = model.predict(text.replace("\n", " "))
    if not label:
        return None
    # fastText returns labels like '__label__en'
    return label[0].replace("__label__", "")


@function_tool()
async def listen_for_commands(context: RunContext) -> str:
    """Wake & Sleep Word Detection with optional Whisper ASR."""

    global is_awake
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Listening for wake/sleep words...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, phrase_time_limit=5)

    asr = get_asr_instance()
    transcript: Optional[str] = None

    if asr is not None:
        try:
            audio_bytes = audio.get_raw_data(convert_rate=16000, convert_width=2)
            transcript = asr.transcribe(audio_bytes, sample_rate=16000)
        except Exception as exc:  # pragma: no cover - best effort fallback
            print(f"[ASR] Whisper pipeline failed: {exc}")

    if not transcript:
        try:
            transcript = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "No recognizable speech detected."
        except Exception as error:
            return f"Error in wake/sleep detection: {error}"

    text = transcript.lower().strip()
    lang = _detect_language(text)
    if lang:
        context.logger.info(f"Detected language: {lang}")

    auto_sleep_msg = check_auto_sleep()
    if auto_sleep_msg:
        return auto_sleep_msg

    if not is_awake:
        if wake_word in text:
            return wake_up()
        return "Clara is sleeping. Ignoring input."

    update_activity()

    if sleep_phrase in text:
        return go_to_sleep()
    if wake_word in text:
        return "Clara is already active."
    return f"Clara (active) heard: {text}"