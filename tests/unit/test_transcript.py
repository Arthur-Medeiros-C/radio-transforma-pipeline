"""Tests for the Transcript contract."""

import pytest
from pydantic import ValidationError

from radio_transforma.models.transcript import Transcript, TranscriptSegment


def _segment(**overrides) -> TranscriptSegment:
    base = {"id": "seg-001", "start": 0.0, "end": 2.5, "text": "Bom dia."}
    base.update(overrides)
    return TranscriptSegment(**base)


def _transcript(**overrides) -> Transcript:
    base = {
        "id": "tr-001",
        "audio_id": "audio-001",
        "model": "faster-whisper",
        "segments": [_segment()],
    }
    base.update(overrides)
    return Transcript(**base)


class TestTranscriptSegment:
    def test_valid_segment(self):
        seg = _segment()
        assert seg.start == 0.0
        assert seg.end == 2.5

    def test_end_equal_to_start_rejected(self):
        with pytest.raises(ValidationError):
            _segment(start=5.0, end=5.0)

    def test_end_before_start_rejected(self):
        with pytest.raises(ValidationError):
            _segment(start=10.0, end=1.0)

    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            _segment(text="")

    def test_confidence_out_of_bounds(self):
        with pytest.raises(ValidationError):
            _segment(confidence=1.5)

    def test_frozen(self):
        seg = _segment()
        with pytest.raises(ValidationError):
            seg.text = "changed"  # type: ignore[misc]


class TestTranscript:
    def test_valid_transcript(self):
        t = _transcript()
        assert t.model == "faster-whisper"
        assert len(t.segments) == 1

    def test_empty_segments_allowed(self):
        t = _transcript(segments=[])
        assert t.segments == []

    def test_full_text_joins_segments(self):
        segs = [
            TranscriptSegment(id="s1", start=0, end=1, text="Olá"),
            TranscriptSegment(id="s2", start=1, end=2, text="mundo."),
        ]
        t = _transcript(segments=segs)
        assert t.full_text == "Olá mundo."

    def test_negative_wer_rejected(self):
        with pytest.raises(ValidationError):
            _transcript(wer=-0.1)

    def test_created_at_has_timezone(self):
        t = _transcript()
        assert t.created_at.tzinfo is not None