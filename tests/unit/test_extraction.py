"""Tests for the ExtractedData contract."""

import pytest
from pydantic import ValidationError

from radio_transforma.models.extraction import (
    Entity,
    EntityType,
    ExtractedData,
    Quote,
    Topic,
)


class TestTopic:
    def test_default_confidence(self):
        t = Topic(name="agricultural policy")
        assert t.confidence == 1.0

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Topic(name="")

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            Topic(name="x", confidence=1.5)


class TestEntity:
    def test_default_type_is_other(self):
        e = Entity(name="Bruxelas")
        assert e.type == EntityType.OTHER

    def test_typed_entity(self):
        e = Entity(name="Bruxelas", type=EntityType.LOCATION)
        assert e.type == EntityType.LOCATION

    def test_mentions_must_be_positive(self):
        with pytest.raises(ValidationError):
            Entity(name="x", mentions=0)


class TestQuote:
    def test_default_position(self):
        q = Quote(text="a mudança de fundo")
        assert q.position == "middle"

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            Quote(text="")


class TestExtractedData:
    def test_empty_collections_default(self):
        d = ExtractedData(transcript_id="tr-001", model="pydantic-ai")
        assert d.topics == []
        assert d.entities == []
        assert d.quotes == []
        assert d.sentiment == "neutral"

    def test_full_payload(self):
        d = ExtractedData(
            transcript_id="tr-001",
            model="pydantic-ai",
            topics=[Topic(name="agriculture")],
            entities=[Entity(name="Bruxelas", type=EntityType.LOCATION)],
            quotes=[Quote(text="a mudança")],
            sentiment="neutral_analytical",
        )
        assert len(d.topics) == 1
        assert d.entities[0].type == EntityType.LOCATION

    def test_frozen(self):
        d = ExtractedData(transcript_id="t", model="m")
        with pytest.raises(ValidationError):
            d.sentiment = "changed"  # type: ignore[misc]

    def test_created_at_has_timezone(self):
        d = ExtractedData(transcript_id="t", model="m")
        assert d.created_at.tzinfo is not None