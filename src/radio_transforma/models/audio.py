"""Audio contracts — the raw input representation for the pipeline.

An `AudioSegment` is the smallest unit of audio the pipeline can ingest.
It represents a single file (reel, interview clip, program excerpt) with
enough metadata to be traceable and reproducible.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AudioSource(StrEnum):
    """Where the audio came from."""

    INSTAGRAM_REEL = "instagram_reel"
    INTERVIEW = "interview"
    PROGRAM = "program"
    MANUAL_UPLOAD = "manual_upload"
    OTHER = "other"


class AudioSegment(BaseModel):
    """A single audio file to be processed by the pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1, description="Stable identifier for this segment.")
    source: AudioSource = Field(..., description="Where the audio came from.")
    duration_seconds: float = Field(..., gt=0, description="Length in seconds.")
    language: str = Field(
        default="pt-PT",
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="BCP-47 language tag (e.g., 'pt-PT').",
    )

    audio_path: str | None = Field(
        default=None, description="Local filesystem path, if applicable."
    )
    audio_url: str | None = Field(default=None, description="Remote URL, if applicable.")

    speakers: int | None = Field(default=None, ge=1, description="Known or expected speaker count.")
    sample_rate_hz: int | None = Field(default=None, gt=0)
    format: str | None = Field(default=None, description="Container/codec (e.g., 'mp3', 'wav').")
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
        description="Content hash for integrity verification.",
    )

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _at_least_one_location(self) -> "AudioSegment":
        if not self.audio_path and not self.audio_url:
            raise ValueError("Either 'audio_path' or 'audio_url' must be provided.")
        return self
