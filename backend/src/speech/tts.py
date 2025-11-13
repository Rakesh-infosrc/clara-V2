"""Text-to-speech utilities leveraging the open-source Coqui TTS project.

The helper exposes a singleton wrapper that attempts to load the multilingual
`xtts_v2` model. If the dependency is missing, callers can detect the `None`
return value and skip audio playback (or choose an alternative backend).
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Optional

try:  # Optional dependency
    from TTS.api import TTS  # type: ignore
except Exception:  # pragma: no cover - optional import
    TTS = None  # type: ignore


@dataclass(slots=True)
class TTSConfig:
    model_name: str = os.getenv("COQUI_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    gpu: bool = os.getenv("COQUI_TTS_USE_GPU", "false").lower() in {"1", "true", "yes"}
    style: str = os.getenv("COQUI_TTS_STYLE", "energetic")
    speed: float = float(os.getenv("COQUI_TTS_SPEED", "1.05"))
    emotion: str = os.getenv("COQUI_TTS_EMOTION", "friendly")


class CoquiTTS:
    """Wrapper around the Coqui TTS API."""

    def __init__(self, config: Optional[TTSConfig] = None) -> None:
        if TTS is None:
            raise RuntimeError(
                "coqui-tts is not installed. Install it to enable free local TTS playback."
            )
        if config is None:
            config = TTSConfig()
        self.config = config
        self._tts = TTS(model_name=config.model_name, progress_bar=False, gpu=config.gpu)

    def synthesize_with_style(self, text: str, language: str, *, style: str | None = None, speed: float | None = None, emotion: str | None = None) -> bytes:
        original_style = self.config.style
        original_speed = self.config.speed
        original_emotion = self.config.emotion
        try:
            if style:
                self.config.style = style
            if speed:
                self.config.speed = speed
            if emotion:
                self.config.emotion = emotion
            return self.synthesize(text, language)
        finally:
            self.config.style = original_style
            self.config.speed = original_speed
            self.config.emotion = original_emotion

    def synthesize(self, text: str, language: str) -> bytes:
        """Generate PCM audio for the provided text in the desired language.

        Args:
            text: Text to speak.
            language: Language code supported by the selected model (e.g. 'en', 'ta', 'te', 'hi').
        Returns:
            PCM 16-bit little-endian bytes ready for playback.
        """
        wav = self._tts.tts(
            text=text,
            language=language,
            speaker=self.config.style if hasattr(self, "config") else None,
            speed=self.config.speed if hasattr(self, "config") else 1.0,
            emotion=self.config.emotion if hasattr(self, "config") else None,
        )
        # coqui returns numpy array float32 in range [-1, 1]; convert to PCM16 bytes

        audio = (wav * 32767).astype("int16")
        return audio.tobytes()


_TTS_LOCK = threading.Lock()
_TTS_INSTANCE: Optional[CoquiTTS] = None


def get_tts_instance() -> Optional[CoquiTTS]:
    """Return a singleton TTS instance if the dependency is available."""
    global _TTS_INSTANCE
    if _TTS_INSTANCE is not None:
        return _TTS_INSTANCE
    with _TTS_LOCK:
        if _TTS_INSTANCE is not None:
            return _TTS_INSTANCE
        try:
            _TTS_INSTANCE = CoquiTTS()
        except RuntimeError:
            _TTS_INSTANCE = None
    return _TTS_INSTANCE
