"""Tests for the query, retrieval and agent contracts."""

import pytest
from pydantic import ValidationError

from radio_transforma.models.query import (
    AgentResponse,
    Citation,
    Query,
    RetrievalResult,
)


class TestQuery:
    def test_default_top_k(self):
        q = Query(id="q1", text="O que é que ele disse?")
        assert q.top_k == 5

    def test_top_k_lower_bound(self):
        with pytest.raises(ValidationError):
            Query(id="q1", text="x", top_k=0)

    def test_top_k_upper_bound(self):
        with pytest.raises(ValidationError):
            Query(id="q1", text="x", top_k=100)

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            Query(id="q1", text="")


class TestRetrievalResult:
    def test_valid(self):
        r = RetrievalResult(chunk_id="c1", content="foo", score=0.85)
        assert r.score == 0.85

    def test_score_above_one_rejected(self):
        with pytest.raises(ValidationError):
            RetrievalResult(chunk_id="c1", content="x", score=1.5)

    def test_score_negative_rejected(self):
        with pytest.raises(ValidationError):
            RetrievalResult(chunk_id="c1", content="x", score=-0.1)


class TestCitation:
    def test_minimal(self):
        c = Citation(source_id="transcription-001")
        assert c.segment_id is None
        assert c.quote is None

    def test_full(self):
        c = Citation(
            source_id="transcription-001",
            segment_id="seg-003",
            quote="a mudança de fundo",
        )
        assert c.segment_id == "seg-003"


class TestAgentResponse:
    def test_valid_minimal(self):
        r = AgentResponse(
            query_id="q1",
            answer="Sim.",
            model="langgraph-gpt-4o",
            latency_ms=2500,
        )
        assert r.latency_ms == 2500
        assert r.citations == []

    def test_negative_latency_rejected(self):
        with pytest.raises(ValidationError):
            AgentResponse(query_id="q1", answer="x", model="m", latency_ms=-1)

    def test_cost_optional(self):
        r = AgentResponse(query_id="q1", answer="x", model="m", latency_ms=100)
        assert r.cost_usd is None

    def test_empty_answer_rejected(self):
        with pytest.raises(ValidationError):
            AgentResponse(query_id="q1", answer="", model="m", latency_ms=100)

    def test_frozen(self):
        r = AgentResponse(query_id="q1", answer="x", model="m", latency_ms=100)
        with pytest.raises(ValidationError):
            r.answer = "changed"  # type: ignore[misc]
