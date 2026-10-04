"""Query contracts — retrieval and agent responses.

Covers the two query paths: low-level retrieval (`RetrievalResult`) and
high-level agent answers (`AgentResponse`). Both are pure outputs; the
query itself is just a prompt with parameters.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Query(BaseModel):
    """A user or system query against the knowledge base."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, str] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """A single retrieved chunk from the vector/relational store."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)
    source_id: Optional[str] = Field(
        default=None, description="Transcript or audio ID this chunk belongs to."
    )


class Citation(BaseModel):
    """A citation attached to an agent response."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(
        ..., min_length=1, description="e.g., 'transcription-001'."
    )
    segment_id: Optional[str] = Field(default=None)
    quote: Optional[str] = Field(default=None)


class AgentResponse(BaseModel):
    """The final response produced by a LangGraph agent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    citations: list[Citation] = Field(default_factory=list)
    model: str = Field(...)
    latency_ms: int = Field(..., ge=0)
    cost_usd: Optional[float] = Field(default=None, ge=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))