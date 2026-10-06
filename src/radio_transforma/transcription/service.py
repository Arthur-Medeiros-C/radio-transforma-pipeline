"""Audio transcription via faster-whisper.

Scope: turn an audio file on disk into a :class:`Transcript`. No audio
download (see AudioRepository), no persistence (see TranscriptRepository),
no Modal wrapper (Block 5). The Whisper model is loaded lazily and its
factory is injectable for tests.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from radio_transforma.models.transcript import Transcript, TranscriptSegment

if TYPE_CHECKING:
    from faster_whisper import WhisperModel


DEFAULT_MODEL_NAME = "large-v3"
DEFAULT_LANGUAGE = "pt-PT"


class TranscriptionServiceError(RuntimeError):
    """Raised when transcription fails."""


def _default_model_factory() -> WhisperModel:
    """Lazy import so CI (which mocks the model) need not load ctranslate2."""
    from faster_whisper import WhisperModel

    return WhisperModel(DEFAULT_MODEL_NAME, device="auto", compute_type="int8")


class TranscriptionService:
    """Transcribe audio files to :class:`Transcript` objects."""

    def __init__(
        self,
        model_factory: Callable[[], WhisperModel] | None = None,
        *,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self._model_factory = model_factory or _default_model_factory
        self._model_name = model_name
        self._model: WhisperModel | None = None

    @property
    def model_name(self) -> str:
        """Identifier of the model this service was configured with."""
        return self._model_name

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def transcribe(
        self,
        audio_id: str,
        audio_path: Path,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> Transcript:
        """Transcribe ``audio_path`` and return a :class:`Transcript`."""
        self._validate_args(audio_id, audio_path, language)

        if not audio_path.is_file():
            raise TranscriptionServiceError(f"audio file not found: {audio_path}")

        model = self._get_model()

        try:
            segments_iter, _info = model.transcribe(str(audio_path), language=language)
            segments = self._collect_segments(segments_iter)
        except Exception as exc:  # noqa: BLE001 — re-raised as domain error
            raise TranscriptionServiceError(
                f"transcription failed for {audio_path}: {exc}"
            ) from exc

        if not segments:
            raise TranscriptionServiceError(f"transcription produced no segments for {audio_path}")

        return Transcript(
            id=str(uuid.uuid4()),
            audio_id=audio_id,
            language=language,
            model=self._model_name,
            wer=None,
            created_at=datetime.now(UTC),
            segments=segments,
        )

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            try:
                self._model = self._model_factory()
            except Exception as exc:  # noqa: BLE001
                raise TranscriptionServiceError(f"failed to load whisper model: {exc}") from exc
        return self._model

    @classmethod
    def _collect_segments(cls, raw_segments: Any) -> tuple[TranscriptSegment, ...]:
        out: list[TranscriptSegment] = []
        for raw in raw_segments:
            text = (getattr(raw, "text", "") or "").strip()
            if not text:
                continue
            out.append(
                TranscriptSegment(
                    id=str(uuid.uuid4()),
                    start=float(raw.start),
                    end=float(raw.end),
                    text=text,
                    confidence=cls._confidence_from(getattr(raw, "avg_logprob", None)),
                )
            )
        return tuple(out)

    @staticmethod
    def _confidence_from(avg_logprob: Any) -> float | None:
        if not isinstance(avg_logprob, (int, float)):
            return None
        return max(0.0, min(1.0, math.exp(float(avg_logprob))))

    @staticmethod
    def _validate_args(audio_id: str, audio_path: Path, language: str) -> None:
        if not isinstance(audio_id, str) or not audio_id.strip():
            raise ValueError("audio_id must be a non-empty string")
        if not isinstance(audio_path, Path):
            raise TypeError("audio_path must be a pathlib.Path")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
