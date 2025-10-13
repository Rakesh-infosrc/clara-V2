"""Utility helpers to audition Clara's multilingual TTS output.

Run the module as a script to generate short "Gen-Z"-styled voice samples for
all supported languages. The resulting WAV files are stored under the
``tts_samples/`` directory (relative to the project root by default).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Tuple

try:  # When executed as part of the src package (``python -m src.speech.preview``)
    from ..language_utils import SUPPORTED_LANGUAGES, get_message
    from .tts import get_tts_instance
except ImportError:  # When executed directly (``python src/speech/preview.py``)
    SRC_ROOT = Path(__file__).resolve().parents[1]
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from language_utils import SUPPORTED_LANGUAGES, get_message  # type: ignore
    from speech.tts import get_tts_instance  # type: ignore

# A short, upbeat sample for each supported language. We reuse the localized
# wake prompt to keep the content topical and ensure proper language coverage.
_SAMPLE_MESSAGES: Iterable[Tuple[str, str]] = tuple(
    (lang, get_message("wake_prompt", lang)) for lang in sorted(SUPPORTED_LANGUAGES)
)

# Tuned parameters that push the voice into a more casual, energetic register.
# You can tweak per-language tone by editing this mapping.
_STYLE_OVERRIDES = {
    "en": {"style": "energetic", "speed": 1.12, "emotion": "excited"},
    "ta": {"style": "energetic", "speed": 1.08, "emotion": "cheerful"},
    "te": {"style": "energetic", "speed": 1.08, "emotion": "cheerful"},
    "hi": {"style": "energetic", "speed": 1.1, "emotion": "friendly"},
}


def generate_samples(output_dir: str | Path = "tts_samples") -> list[Path]:
    """Generate Gen-Z styled samples for all supported languages.

    Args:
        output_dir: Directory where WAV files should be written.

    Returns:
        List of paths to the generated audio files.
    """
    tts = get_tts_instance()
    if tts is None:
        raise RuntimeError(
            "coqui-tts is not installed. Install it or adjust requirements to preview samples."
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files: list[Path] = []

    for lang, text in _SAMPLE_MESSAGES:
        overrides = _STYLE_OVERRIDES.get(lang, {})
        audio_bytes = tts.synthesize_with_style(
            text,
            lang,
            style=overrides.get("style"),
            speed=overrides.get("speed"),
            emotion=overrides.get("emotion"),
        )

        file_path = output_path / f"clara_genz_{lang}.wav"
        file_path.write_bytes(audio_bytes)
        generated_files.append(file_path)

    return generated_files


if __name__ == "__main__":
    files = generate_samples()
    for file in files:
        print(f"✅ Generated sample: {file}")
