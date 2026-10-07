"""Unit tests for radio_transforma.cli."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from radio_transforma import cli
from radio_transforma.dry_run import (
    NullAudioRepository,
    NullTranscriptionService,
    NullTranscriptRepository,
)
from radio_transforma.ingestion.orchestrator import IngestionError

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def test_build_parser_rejects_missing_subcommand() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_parser_ingest_defaults() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["ingest", "audio.mp3"])
    assert args.file == Path("audio.mp3")
    assert args.audio_id is None
    assert args.language == "pt-PT"
    assert args.dry_run is False
    assert args.func is cli._cmd_ingest


def test_build_parser_accepts_explicit_audio_id_and_language() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["ingest", "audio.mp3", "--audio-id", "abc", "--language", "en-GB"])
    assert args.audio_id == "abc"
    assert args.language == "en-GB"


def test_build_parser_dry_run_flag() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["ingest", "audio.mp3", "--dry-run"])
    assert args.dry_run is True


def test_build_parser_verbose_flag() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["--verbose", "ingest", "audio.mp3"])
    assert args.verbose is True


# ---------------------------------------------------------------------------
# _build_orchestrator: real vs dry-run wiring
# ---------------------------------------------------------------------------


def test_build_orchestrator_wires_real_dependencies(monkeypatch) -> None:
    fake_client = object()
    monkeypatch.setattr(cli, "get_supabase_client", lambda: fake_client)

    captured: dict[str, object] = {}

    def fake_audio_repo(client: object) -> str:
        captured["audio_client"] = client
        return "audio_repo"

    def fake_transcript_repo(client: object) -> str:
        captured["transcript_client"] = client
        return "transcript_repo"

    def fake_transcription_service() -> str:
        return "transcription_service"

    class FakeOrchestrator:
        def __init__(self, **kwargs: object) -> None:
            captured["orchestrator_kwargs"] = kwargs

    monkeypatch.setattr(cli, "AudioRepository", fake_audio_repo)
    monkeypatch.setattr(cli, "TranscriptRepository", fake_transcript_repo)
    monkeypatch.setattr(cli, "TranscriptionService", fake_transcription_service)
    monkeypatch.setattr(cli, "IngestionOrchestrator", FakeOrchestrator)

    cli._build_orchestrator(dry_run=False)

    assert captured["audio_client"] is fake_client
    assert captured["transcript_client"] is fake_client
    assert captured["orchestrator_kwargs"] == {
        "audio_repository": "audio_repo",
        "transcription_service": "transcription_service",
        "transcript_repository": "transcript_repo",
    }


def test_build_orchestrator_uses_null_objects_on_dry_run(monkeypatch) -> None:
    # Guard: dry-run must not touch the Supabase client factory at all.
    monkeypatch.setattr(
        cli,
        "get_supabase_client",
        lambda: pytest.fail("dry-run must not build the Supabase client"),
    )

    captured: dict[str, object] = {}

    class FakeOrchestrator:
        def __init__(self, **kwargs: object) -> None:
            captured["orchestrator_kwargs"] = kwargs

    monkeypatch.setattr(cli, "IngestionOrchestrator", FakeOrchestrator)

    cli._build_orchestrator(dry_run=True)

    kwargs = captured["orchestrator_kwargs"]
    assert isinstance(kwargs["audio_repository"], NullAudioRepository)
    assert isinstance(kwargs["transcription_service"], NullTranscriptionService)
    assert isinstance(kwargs["transcript_repository"], NullTranscriptRepository)


# ---------------------------------------------------------------------------
# _cmd_ingest: JSON contract
# ---------------------------------------------------------------------------


def test_cmd_ingest_success_emits_pure_json(monkeypatch, capsys) -> None:
    orchestrator = MagicMock()
    orchestrator.ingest.return_value = MagicMock(
        audio_id="audio-1",
        segments=(object(), object()),
    )
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/audio.mp3"),
        audio_id="audio-1",
        language="pt-PT",
        dry_run=False,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)  # must be valid JSON, exactly
    assert payload == {
        "status": "success",
        "audio_id": "audio-1",
        "segments_count": 2,
        "dry_run": False,
    }
    assert captured.err == ""


def test_cmd_ingest_success_dry_run_flags_payload(monkeypatch, capsys) -> None:
    orchestrator = MagicMock()
    orchestrator.ingest.return_value = MagicMock(audio_id="audio-1", segments=())
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/audio.mp3"),
        audio_id="audio-1",
        language="pt-PT",
        dry_run=True,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["segments_count"] == 0


def test_cmd_ingest_falls_back_to_file_stem(monkeypatch, capsys) -> None:
    orchestrator = MagicMock()
    orchestrator.ingest.return_value = MagicMock(audio_id="my-recording", segments=())
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/my-recording.wav"),
        audio_id=None,
        language="pt-PT",
        dry_run=False,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 0
    assert orchestrator.ingest.call_args.kwargs["audio_id"] == "my-recording"
    assert json.loads(capsys.readouterr().out)["audio_id"] == "my-recording"


def test_cmd_ingest_ingestion_error_emits_json_and_stderr(monkeypatch, capsys) -> None:
    orchestrator = MagicMock()
    # IngestionError signature is (stage, audio_id, message) — pass positional.
    orchestrator.ingest.side_effect = IngestionError("transcribe", "audio-1", "boom")
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/audio.mp3"),
        audio_id="audio-1",
        language="pt-PT",
        dry_run=False,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    # IngestionError.__str__ returns "[stage] audio_id: message".
    assert payload == {
        "status": "error",
        "stage": "transcribe",
        "audio_id": "audio-1",
        "message": "[transcribe] audio-1: boom",
    }
    assert "stage=transcribe" in captured.err
    assert "audio-1" in captured.err


def test_cmd_ingest_unexpected_error_is_wrapped(monkeypatch, capsys) -> None:
    orchestrator = MagicMock()
    orchestrator.ingest.side_effect = RuntimeError("kaboom")
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/audio.mp3"),
        audio_id="audio-1",
        language="pt-PT",
        dry_run=False,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "error"
    assert payload["stage"] == "unexpected"
    assert payload["audio_id"] == "audio-1"
    assert "kaboom" in payload["message"]
    assert "kaboom" in captured.err


# ---------------------------------------------------------------------------
# stdout isolation: 3rd-party writes during the pipeline must not leak
# ---------------------------------------------------------------------------


def test_pipeline_stdout_pollution_is_redirected_to_stderr(monkeypatch, capsys) -> None:
    """A 3rd-party ``print()`` inside the pipeline must not reach stdout."""

    def noisy_ingest(**_kwargs):
        print("faster-whisper progress: 100%")
        return MagicMock(audio_id="audio-1", segments=())

    orchestrator = MagicMock()
    orchestrator.ingest.side_effect = noisy_ingest
    monkeypatch.setattr(cli, "_build_orchestrator", lambda *, dry_run: orchestrator)

    args = argparse.Namespace(
        file=Path("/tmp/audio.mp3"),
        audio_id="audio-1",
        language="pt-PT",
        dry_run=False,
    )
    rc = cli._cmd_ingest(args)

    assert rc == 0
    captured = capsys.readouterr()
    # stdout must contain ONLY the JSON envelope.
    payload = json.loads(captured.out)
    assert payload["status"] == "success"
    # The noisy print must have landed on stderr instead.
    assert "faster-whisper progress" in captured.err


def test_redirect_stdout_context_manager_restores_original() -> None:
    original = sys.stdout
    with cli._redirect_stdout_to_stderr():
        assert sys.stdout is sys.stderr
    assert sys.stdout is original


# ---------------------------------------------------------------------------
# main(): dispatch + logging level
# ---------------------------------------------------------------------------


def test_main_dispatches_to_handler(monkeypatch) -> None:
    parser = MagicMock()
    args = MagicMock(verbose=False)
    args.func.return_value = 0
    parser.parse_args.return_value = args
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    basic_config = MagicMock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)
    monkeypatch.setattr(logging.getLogger("faster_whisper"), "setLevel", MagicMock())

    rc = cli.main(["ingest", "audio.mp3"])

    assert rc == 0
    parser.parse_args.assert_called_once_with(["ingest", "audio.mp3"])
    args.func.assert_called_once_with(args)
    assert basic_config.call_args.kwargs["level"] == logging.INFO
    assert basic_config.call_args.kwargs["stream"] is sys.stderr


def test_main_enables_debug_when_verbose(monkeypatch) -> None:
    parser = MagicMock()
    args = MagicMock(verbose=True)
    args.func.return_value = 0
    parser.parse_args.return_value = args
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    basic_config = MagicMock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)
    monkeypatch.setattr(logging.getLogger("faster_whisper"), "setLevel", MagicMock())

    cli.main(["--verbose", "ingest", "audio.mp3"])

    assert basic_config.call_args.kwargs["level"] == logging.DEBUG


def test_main_silences_faster_whisper(monkeypatch) -> None:
    parser = MagicMock()
    args = MagicMock(verbose=True)
    args.func.return_value = 0
    parser.parse_args.return_value = args
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    monkeypatch.setattr(logging, "basicConfig", MagicMock())
    fw_logger = logging.getLogger("faster_whisper")
    set_level = MagicMock()
    monkeypatch.setattr(fw_logger, "setLevel", set_level)

    cli.main(["ingest", "audio.mp3"])

    set_level.assert_called_once_with(logging.WARNING)
