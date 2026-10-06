"""Transcription: audio → text via faster-whisper."""

from radio_transforma.transcription.service import (
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL_NAME,
    TranscriptionService,
    TranscriptionServiceError,
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "DEFAULT_MODEL_NAME",
    "TranscriptionService",
    "TranscriptionServiceError",
]
