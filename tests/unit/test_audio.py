"""Tests for the AudioSegment contract."""

import pytest
from pydantic import ValidationError

from radio_transforma.models.audio import AudioSegment, AudioSource


def _valid_audio(**overrides) -> dict:
    base = {
        "id": "audio-001",
        "source": AudioSource.INSTAGRAM_REEL,
        "duration_seconds": 45.0,
        "audio_url": "https://example.com/audio.mp3",
    }
    base.update(overrides)
    return base


class TestAudioSegmentValid:
    def test_minimal_valid_segment(self):
        seg = AudioSegment(**_valid_audio())
        assert seg.id == "audio-001"
        assert seg.source == AudioSource.INSTAGRAM_REEL
        assert seg.language == "pt-PT"
        assert seg.duration_seconds == 45.0

    def test_with_local_path_only(self):
        seg = AudioSegment(**_valid_audio(audio_url=None, audio_path="/tmp/a.mp3"))
        assert seg.audio_path == "/tmp/a.mp3"
        assert seg.audio_url is None

    def test_default_language_is_pt_pt(self):
        seg = AudioSegment(**_valid_audio())
        assert seg.language == "pt-PT"

    def test_ingested_at_has_timezone(self):
        seg = AudioSegment(**_valid_audio())
        assert seg.ingested_at.tzinfo is not None


class TestAudioSegmentValidation:
    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(id=""))

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(duration_seconds=-1))

    def test_zero_duration_rejected(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(duration_seconds=0))

    def test_invalid_language_format(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(language="portuguese"))

    def test_missing_location_rejected(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(audio_url=None, audio_path=None))

    def test_invalid_sha256(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(checksum_sha256="not-a-hash"))

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            AudioSegment(**_valid_audio(unexpected="x"))


class TestAudioSegmentImmutability:
    def test_frozen(self):
        seg = AudioSegment(**_valid_audio())
        with pytest.raises(ValidationError):
            seg.id = "changed"  # type: ignore[misc]
