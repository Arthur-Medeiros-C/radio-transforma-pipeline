"""Unit tests for radio_transforma.dry_run Null Objects."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from radio_transforma.dry_run import (
    NullAudioRepository,
    NullTranscriptionService,
    NullTranscriptRepository,
)
from radio_transforma.models.transcript import Transcript


def test_null_audio_repository_upload_returns_fake_path() -> None:
    assert NullAudioRepository().upload("any/path.mp3") == "dry-run://audio"


def test_null_audio_repository_download_returns_empty_bytes() -> None:
    assert NullAudioRepository().download("any/path.mp3") == b""


def test_null_audio_repository_create_signed_url() -> None:
    assert NullAudioRepository().create_signed_url("any/path.mp3") == "dry-run://signed"


def test_null_audio_repository_exists_forces_false() -> None:
    # Must return False so the orchestrator exercises the upload branch.
    assert NullAudioRepository().exists("any/path.mp3") is False


def test_null_audio_repository_delete_is_noop() -> None:
    assert NullAudioRepository().delete("any/path.mp3") is None


def test_null_transcript_repository_save_is_noop() -> None:
    assert NullTranscriptRepository().save(object()) is None


def test_null_transcript_repository_get_returns_none() -> None:
    # Must return None so the orchestrator exercises transcribe+persist.
    assert NullTranscriptRepository().get("audio-1", "pt-PT", "model") is None


def test_null_transcript_repository_list_for_audio_empty() -> None:
    assert NullTranscriptRepository().list_for_audio("audio-1") == []


def test_null_transcript_repository_delete_is_noop() -> None:
    assert NullTranscriptRepository().delete("audio-1") is None


def test_null_transcription_service_model_name() -> None:
    assert NullTranscriptionService().model_name == "dry-run"


def test_null_transcription_service_raises_when_file_missing(
    tmp_path: Path,
) -> None:
    service = NullTranscriptionService()
    with pytest.raises(FileNotFoundError, match="dry-run"):
        service.transcribe("audio-1", tmp_path / "missing.mp3")


def test_null_transcription_service_returns_synthetic_transcript(
    tmp_path: Path,
) -> None:
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"fake")

    transcript = NullTranscriptionService().transcribe("audio-1", audio, language="pt-PT")

    assert isinstance(transcript, Transcript)
    assert transcript.audio_id == "audio-1"
    assert transcript.language == "pt-PT"
    assert transcript.model == "dry-run"
    assert transcript.id == "dry-run-audio-1"
    assert len(transcript.segments) == 1
    assert transcript.segments[0].text == "[dry-run segment]"
    assert transcript.created_at.tzinfo is not None
    # Sanity: tz-aware UTC timestamp (see data contracts convention).
    assert transcript.created_at.tzinfo == UTC
    # Silence linter on unused import (kept for future assertions).
    _ = datetime
