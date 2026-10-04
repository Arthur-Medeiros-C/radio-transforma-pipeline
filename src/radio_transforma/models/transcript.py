"""Transcript contracts — the output of the transcription phase.

A `Transcript` is a collection of `TranscriptSegment`s plus document-level
metadata (which model produced it, when, and — optionally — how accurate
it was against a golden dataset).
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TranscriptSegment(BaseModel):
    """A single timed segment of transcribed text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    start: float = Field(..., ge=0, description="Start time in seconds.")
    end: float = Field(..., gt=0, description="End time in seconds.")
    text: str = Field(..., min_length=1)

    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Model confidence for this segment."
    )
    speaker: str | None = Field(default=None, description="Speaker label, if diarised.")

    @model_validator(mode="after")
    def _end_after_start(self) -> "TranscriptSegment":
        if self.end <= self.start:
            raise ValueError("'end' must be greater than 'start'.")
        return self


class Transcript(BaseModel):
    """A complete transcript for one audio segment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    audio_id: str = Field(..., min_length=1, description="References AudioSegment.id.")
    language: str = Field(default="pt-PT", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")

    model: str = Field(..., description="Transcription model name (e.g., 'faster-whisper').")
    model_version: str | None = Field(default=None, description="Model version / size.")
    segments: list[TranscriptSegment] = Field(default_factory=list)

    wer: float | None = Field(
        default=None,
        ge=0.0,
        description="Word error rate, if measured against ground truth.",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def full_text(self) -> str:
        """Concatenated text of all segments, space-joined."""
        return " ".join(seg.text.strip() for seg in self.segments)
