"""Audio contracts — the raw input representation for the pipeline.

An `AudioSegment` is the smallest unit of audio the pipeline can ingest.
It represents a single file (reel, interview clip, program excerpt) with
enough metadata to be traceable and reproducible.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AudioSource(str, Enum):
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

    audio_path: Optional[str] = Field(
        default=None, description="Local filesystem path, if applicable."
    )
    audio_url: Optional[str] = Field(
        default=None, description="Remote URL, if applicable."
    )

    speakers: Optional[int] = Field(
        default=None, ge=1, description="Known or expected speaker count."
    )
    sample_rate_hz: Optional[int] = Field(default=None, gt=0)
    format: Optional[str] = Field(
        default=None, description="Container/codec (e.g., 'mp3', 'wav')."
    )
    checksum_sha256: Optional[str] = Field(
        default=None,
        pattern=r"^[a-f0-9]{64}$",
        description="Content hash for integrity verification.",
    )

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _at_least_one_location(self) -> "AudioSegment":
        if not self.audio_path and not self.audio_url:
            raise ValueError("Either 'audio_path' or 'audio_url' must be provided.")
        return self