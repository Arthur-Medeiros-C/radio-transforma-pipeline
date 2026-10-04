"""Extraction contracts — structured data derived from a transcript.

The output of the semantic extraction phase: topics, entities, sentiment,
and quotable lines. All fields are deliberately minimal for V0.1 and will
expand as real needs emerge.
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EntityType(StrEnum):
    """Known entity categories."""

    PERSON = "person"
    LOCATION = "location"
    ORGANIZATION = "organization"
    POLICY = "policy"
    GEOPOLITICAL_ENTITY = "geopolitical_entity"
    EVENT = "event"
    OTHER = "other"


class Topic(BaseModel):
    """A theme detected in a transcript."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Entity(BaseModel):
    """A named entity mentioned in a transcript."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1)
    type: EntityType = Field(default=EntityType.OTHER)
    mentions: int = Field(default=1, ge=1)


class Quote(BaseModel):
    """A quotable line extracted from a transcript."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(..., min_length=1)
    position: str = Field(
        default="middle",
        description="Rough position in source: 'start', 'middle', 'end'.",
    )
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, gt=0)


class ExtractedData(BaseModel):
    """Structured data extracted from a transcript."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transcript_id: str = Field(..., min_length=1)
    model: str = Field(..., description="Extraction model name.")
    topics: list[Topic] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    sentiment: str = Field(default="neutral")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
