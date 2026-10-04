"""Data contracts for the Radio Transforma pipeline.

All inter-module data flows through these Pydantic models. They are the
single source of truth for what each phase of the pipeline consumes and
produces.
"""

from radio_transforma.models.audio import AudioSegment, AudioSource
from radio_transforma.models.extraction import (
    Entity,
    EntityType,
    ExtractedData,
    Quote,
    Topic,
)
from radio_transforma.models.query import (
    AgentResponse,
    Citation,
    Query,
    RetrievalResult,
)
from radio_transforma.models.transcript import Transcript, TranscriptSegment

__all__ = [
    "AgentResponse",
    "AudioSegment",
    "AudioSource",
    "Citation",
    "Entity",
    "EntityType",
    "ExtractedData",
    "Query",
    "Quote",
    "RetrievalResult",
    "Topic",
    "Transcript",
    "TranscriptSegment",
]
