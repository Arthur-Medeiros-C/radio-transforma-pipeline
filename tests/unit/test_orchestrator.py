"""Unit tests for :mod:`radio_transforma.ingestion.orchestrator`."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from radio_transforma.ingestion.orchestrator import (
    IngestionError,
    IngestionOrchestrator,
)
from radio_transforma.models.transcript import Transcript, TranscriptSegment
from radio_transforma.storage.audio_repository import AudioRepositoryError
from radio_transforma.storage.transcript_repository import TranscriptRepositoryError
from radio_transforma.transcription.service import TranscriptionServiceError

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _segment(segment_id: str = "s-1") -> TranscriptSegment:
    return TranscriptSegment(id=segment_id, start=0.0, end=1.0, text="olá", confidence=0.9)


def _transcript(
    audio_id: str = "a-1",
    language: str = "pt-PT",
    model: str = "large-v3",
    segments: tuple[TranscriptSegment, ...] | None = None,
) -> Transcript:
    return Transcript(
        id="t-1",
        audio_id=audio_id,
        language=language,
        model=model,
        wer=None,
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        segments=(_segment(),) if segments is None else segments,
    )


@pytest.fixture()
def audio_repo() -> MagicMock:
    repo = MagicMock(name="audio_repo")
    repo.exists.return_value = False
    return repo


@pytest.fixture()
def transcriber() -> MagicMock:
    t = MagicMock(name="transcriber")
    t.model_name = "large-v3"
    t.transcribe.return_value = _transcript()
    return t


@pytest.fixture()
def transcripts() -> MagicMock:
    t = MagicMock(name="transcripts")
    t.list_for_audio.return_value = []
    return t


@pytest.fixture()
def orchestrator(
    audio_repo: MagicMock, transcriber: MagicMock, transcripts: MagicMock
) -> IngestionOrchestrator:
    return IngestionOrchestrator(audio_repo, transcriber, transcripts)


@pytest.fixture()
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "ep01.mp3"
    path.write_bytes(b"\x00\x01\x02")
    return path


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


def test_ingest_happy_path(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    transcriber: MagicMock,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    result = orchestrator.ingest("a-1", audio_file)

    assert result.audio_id == "a-1"
    audio_repo.exists.assert_called_once_with("audio/a-1.mp3")
    audio_repo.upload.assert_called_once()
    transcriber.transcribe.assert_called_once_with("a-1", audio_file, language="pt-PT")
    transcripts.save.assert_called_once_with(result)


def test_ingest_upload_carries_mp3_content_type(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    audio_file: Path,
) -> None:
    orchestrator.ingest("a-1", audio_file)

    _, _, kwargs = audio_repo.upload.mock_calls[0]
    assert kwargs["content_type"] == "audio/mpeg"


def test_ingest_upload_carries_wav_content_type(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    tmp_path: Path,
) -> None:
    wav = tmp_path / "ep.wav"
    wav.write_bytes(b"\x00")

    orchestrator.ingest("a-1", wav)

    _, _, kwargs = audio_repo.upload.mock_calls[0]
    assert kwargs["content_type"] == "audio/wav"


def test_ingest_unknown_suffix_falls_back_to_octet_stream(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    tmp_path: Path,
) -> None:
    weird = tmp_path / "ep.xyz"
    weird.write_bytes(b"\x00")

    orchestrator.ingest("a-1", weird)

    _, _, kwargs = audio_repo.upload.mock_calls[0]
    assert kwargs["content_type"] == "application/octet-stream"


def test_ingest_uses_lowercase_suffix_in_remote_path(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    tmp_path: Path,
) -> None:
    upper = tmp_path / "EP.MP3"
    upper.write_bytes(b"\x00")

    orchestrator.ingest("a-1", upper)

    audio_repo.exists.assert_called_once_with("audio/a-1.mp3")


# --------------------------------------------------------------------------- #
# Upload behaviour                                                            #
# --------------------------------------------------------------------------- #


def test_ingest_skips_upload_when_object_exists(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    audio_file: Path,
) -> None:
    audio_repo.exists.return_value = True

    orchestrator.ingest("a-1", audio_file)

    audio_repo.upload.assert_not_called()


def test_ingest_uploads_when_object_missing(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    audio_file: Path,
) -> None:
    audio_repo.exists.return_value = False

    orchestrator.ingest("a-1", audio_file)

    audio_repo.upload.assert_called_once()


def test_ingest_upload_error_is_wrapped(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    audio_file: Path,
) -> None:
    audio_repo.upload.side_effect = AudioRepositoryError("bucket down")

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", audio_file)

    assert exc_info.value.stage == "upload"
    assert exc_info.value.audio_id == "a-1"
    assert "bucket down" in str(exc_info.value)


def test_ingest_read_file_error_is_wrapped(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    audio_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self: Path) -> bytes:
        raise OSError("disk read error")

    monkeypatch.setattr(Path, "read_bytes", boom)

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", audio_file)

    assert exc_info.value.stage == "upload"
    assert "disk read error" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Idempotency                                                                 #
# --------------------------------------------------------------------------- #


def test_ingest_returns_existing_complete_transcript(
    orchestrator: IngestionOrchestrator,
    audio_repo: MagicMock,
    transcriber: MagicMock,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    existing = _transcript()
    transcripts.list_for_audio.return_value = [existing]

    result = orchestrator.ingest("a-1", audio_file)

    assert result is existing
    audio_repo.exists.assert_not_called()
    audio_repo.upload.assert_not_called()
    transcriber.transcribe.assert_not_called()
    transcripts.save.assert_not_called()


def test_ingest_ignores_orphan_transcript(
    orchestrator: IngestionOrchestrator,
    transcriber: MagicMock,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    orphan = _transcript(segments=())
    transcripts.list_for_audio.return_value = [orphan]

    orchestrator.ingest("a-1", audio_file)

    transcriber.transcribe.assert_called_once()
    transcripts.save.assert_called_once()


def test_ingest_ignores_transcript_with_different_language(
    orchestrator: IngestionOrchestrator,
    transcriber: MagicMock,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    other = _transcript(language="en")
    transcripts.list_for_audio.return_value = [other]

    orchestrator.ingest("a-1", audio_file, language="pt-PT")

    transcriber.transcribe.assert_called_once()


def test_ingest_ignores_transcript_with_different_model(
    orchestrator: IngestionOrchestrator,
    transcriber: MagicMock,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    other = _transcript(model="medium")
    transcripts.list_for_audio.return_value = [other]

    orchestrator.ingest("a-1", audio_file)

    transcriber.transcribe.assert_called_once()


def test_ingest_idempotency_lookup_error_is_wrapped(
    orchestrator: IngestionOrchestrator,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    transcripts.list_for_audio.side_effect = TranscriptRepositoryError("db down")

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", audio_file)

    assert exc_info.value.stage == "idempotency"
    assert "db down" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Transcribe & persist failures                                               #
# --------------------------------------------------------------------------- #


def test_ingest_transcribe_error_is_wrapped(
    orchestrator: IngestionOrchestrator,
    transcriber: MagicMock,
    audio_file: Path,
) -> None:
    transcriber.transcribe.side_effect = TranscriptionServiceError("gpu boom")

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", audio_file)

    assert exc_info.value.stage == "transcribe"
    assert "gpu boom" in str(exc_info.value)


def test_ingest_persist_error_is_wrapped(
    orchestrator: IngestionOrchestrator,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    transcripts.save.side_effect = TranscriptRepositoryError("pk violation")

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", audio_file)

    assert exc_info.value.stage == "persist"
    assert "pk violation" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Validation                                                                  #
# --------------------------------------------------------------------------- #


def test_ingest_missing_local_file_raises(
    orchestrator: IngestionOrchestrator, tmp_path: Path
) -> None:
    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-1", tmp_path / "nope.mp3")

    assert exc_info.value.stage == "validate"
    assert "file not found" in str(exc_info.value)


@pytest.mark.parametrize("bad_id", ["", "   ", None, 123])
def test_ingest_rejects_invalid_audio_id(
    orchestrator: IngestionOrchestrator, audio_file: Path, bad_id: object
) -> None:
    with pytest.raises(ValueError):
        orchestrator.ingest(bad_id, audio_file)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_lang", ["", "   ", None, 123])
def test_ingest_rejects_invalid_language(
    orchestrator: IngestionOrchestrator, audio_file: Path, bad_lang: object
) -> None:
    with pytest.raises(ValueError):
        orchestrator.ingest("a-1", audio_file, language=bad_lang)  # type: ignore[arg-type]


def test_ingest_rejects_non_path(orchestrator: IngestionOrchestrator) -> None:
    with pytest.raises(TypeError):
        orchestrator.ingest("a-1", "not/a/path")  # type: ignore[arg-type]


def test_error_message_includes_stage_and_id(
    orchestrator: IngestionOrchestrator,
    transcripts: MagicMock,
    audio_file: Path,
) -> None:
    transcripts.save.side_effect = TranscriptRepositoryError("boom")

    with pytest.raises(IngestionError) as exc_info:
        orchestrator.ingest("a-42", audio_file)

    message = str(exc_info.value)
    assert "[persist]" in message
    assert "a-42" in message
