"""ASR utilities using open-source backends (e.g., faster-whisper).

This module exposes a lazy-initialised Whisper-based recogniser that falls back to
`speech_recognition`'s Google backend when the optional dependencies are not
installed. The goal is to keep the assistant functional without incurring paid
API costs, while still allowing developers to opt into the heavier models when
available locally.
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Optional

try:  # Optional dependency
    import numpy as np
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover - optional import
    WhisperModel = None  # type: ignore
    np = None  # type: ignore


@dataclass(slots=True)
class ASRConfig:
    """Runtime configuration for the ASR backend."""

    model_size: str = os.getenv("WHISPER_MODEL_SIZE", "medium")
    device: str = os.getenv("WHISPER_DEVICE", "auto")
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


class WhisperASR:
    """Wrapper around `faster-whisper` with simple streaming support."""

    def __init__(self, config: Optional[ASRConfig] = None) -> None:
        if WhisperModel is None:
            raise RuntimeError(
                "faster-whisper is not installed. Install it to enable the free local ASR pipeline."
            )

        if config is None:
            config = ASRConfig()

        device = config.device
        if device == "auto":
            # GPU if available, else CPU
            try:
                import torch  # type: ignore

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:  # pragma: no cover - torch optional
                device = "cpu"

        self._model = WhisperModel(config.model_size, device=device, compute_type=config.compute_type)

    def transcribe(self, audio_bytes: bytes, sample_rate: int) -> str:
        if np is None:
            raise RuntimeError("NumPy is required when using the Whisper ASR backend.")

        # Convert raw audio data (signed 16-bit PCM) into float32 numpy array.
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype("float32") / 32768.0
        segments, _ = self._model.transcribe(
            audio_array,
            beam_size=5,
            language=None,  # Auto-detect language, suitable for code-mixed speech
            temperature=0.0,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript


# --- Lazy singleton helpers -------------------------------------------------
_ASR_LOCK = threading.Lock()
_ASR_INSTANCE: Optional[WhisperASR] = None


def get_asr_instance() -> Optional[WhisperASR]:
    """Return a singleton Whisper ASR instance if dependencies are installed."""

    global _ASR_INSTANCE
    if _ASR_INSTANCE is not None:
        return _ASR_INSTANCE

    with _ASR_LOCK:
        if _ASR_INSTANCE is not None:
            return _ASR_INSTANCE
        try:
            _ASR_INSTANCE = WhisperASR()
        except RuntimeError:
            # Dependencies missing – caller should fallback to cloud/google ASR.
            _ASR_INSTANCE = None
    return _ASR_INSTANCE
