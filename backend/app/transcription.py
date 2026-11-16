"""Local speech-to-text using faster-whisper.

The model is loaded lazily so the web process does not pay the memory cost
until a student actually uses voice input. Raw audio is written to a temporary
file only for the duration of transcription and is then deleted.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_model: Any = None


def _load_model() -> Any:
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError("faster-whisper is not installed on this server") from exc

        logger.info("Loading faster-whisper model '%s'", settings.whisper_model)
        _model = WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
            download_root="/home/qaai/.cache/whisper",
        )
    return _model


def transcribe_bytes(data: bytes, suffix: str = ".webm") -> dict[str, Any]:
    if not settings.whisper_enabled:
        raise RuntimeError("Voice transcription is disabled")

    model = _load_model()
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = handle.name
    try:
        handle.write(data)
        handle.close()
        segments, info = model.transcribe(path, beam_size=1, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {
            "text": text,
            "language": getattr(info, "language", None),
            "duration": getattr(info, "duration", None),
        }
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
