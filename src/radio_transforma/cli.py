"""Command-line entrypoint for the Radio Transforma pipeline.

Usage::

    python -m radio_transforma ingest <file> [--audio-id ID] [--language LANG] [--dry-run]

Contract:

- ``--dry-run`` swaps the effectful dependencies (AudioRepository,
  TranscriptRepository, TranscriptionService) for Null Objects. Input
  validation still runs; no network, no GPU, no database.
- ``--audio-id`` defaults to the file stem when omitted.
- **stdout is machine-readable only.** On success it emits a single JSON
  object; on failure it emits a JSON error envelope. Human-readable
  diagnostics go to stderr. The stdout of 3rd-party libraries invoked
  during the pipeline is redirected to stderr for the duration of the call.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from radio_transforma.dry_run import (
    NullAudioRepository,
    NullTranscriptionService,
    NullTranscriptRepository,
)
from radio_transforma.ingestion.orchestrator import (
    IngestionError,
    IngestionOrchestrator,
)
from radio_transforma.storage.audio_repository import AudioRepository
from radio_transforma.storage.supabase_client import get_supabase_client
from radio_transforma.storage.transcript_repository import TranscriptRepository
from radio_transforma.transcription.service import TranscriptionService

logger = logging.getLogger(__name__)


@contextmanager
def _redirect_stdout_to_stderr() -> Iterator[None]:
    """Redirect ``sys.stdout`` to ``sys.stderr`` for the duration of the block.

    Third-party libraries (faster-whisper, tqdm, FFmpeg wrappers) may write
    progress or diagnostics to stdout. This keeps our JSON output as the only
    thing on stdout.
    """
    original_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original_stdout


def _build_orchestrator(*, dry_run: bool) -> IngestionOrchestrator:
    """Wire the Phase 1 dependencies, real or Null, based on ``dry_run``."""
    if dry_run:
        return IngestionOrchestrator(
            audio_repository=NullAudioRepository(),
            transcription_service=NullTranscriptionService(),
            transcript_repository=NullTranscriptRepository(),
        )
    client = get_supabase_client()
    return IngestionOrchestrator(
        audio_repository=AudioRepository(client),
        transcription_service=TranscriptionService(),
        transcript_repository=TranscriptRepository(client),
    )


def _emit_json(payload: dict[str, Any]) -> None:
    """Write a single JSON object to the real stdout and flush."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _cmd_ingest(args: argparse.Namespace) -> int:
    """Run a single end-to-end ingestion from a local audio file."""
    audio_id = args.audio_id or args.file.stem
    dry_run: bool = args.dry_run

    try:
        orchestrator = _build_orchestrator(dry_run=dry_run)
        with _redirect_stdout_to_stderr():
            transcript = orchestrator.ingest(
                audio_id=audio_id,
                audio_path=args.file,
                language=args.language,
            )
    except IngestionError as exc:
        print(
            f"ERROR stage={exc.stage} audio_id={exc.audio_id}: {exc}",
            file=sys.stderr,
        )
        _emit_json(
            {
                "status": "error",
                "stage": exc.stage,
                "audio_id": exc.audio_id,
                "message": str(exc),
            }
        )
        return 1
    except Exception as exc:  # defensive: never let a traceback corrupt stdout
        print(f"ERROR unexpected: {exc!r}", file=sys.stderr)
        _emit_json(
            {
                "status": "error",
                "stage": "unexpected",
                "audio_id": audio_id,
                "message": str(exc),
            }
        )
        return 1

    _emit_json(
        {
            "status": "success",
            "audio_id": transcript.audio_id,
            "segments_count": len(transcript.segments),
            "dry_run": dry_run,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(prog="radio_transforma")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug-level logging on stderr",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser(
        "ingest",
        help="ingest a local audio file into the pipeline",
    )
    ingest.add_argument("file", type=Path, help="path to the audio file")
    ingest.add_argument(
        "--audio-id",
        default=None,
        help="stable identifier for the audio (default: file stem)",
    )
    ingest.add_argument(
        "--language",
        default="pt-PT",
        help="BCP-47 language tag (default: pt-PT)",
    )
    ingest.add_argument(
        "--dry-run",
        action="store_true",
        help="run the pipeline with Null dependencies (no network, no GPU)",
    )
    ingest.set_defaults(func=_cmd_ingest)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, configure logging, dispatch to the chosen command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # faster-whisper is chatty at INFO; keep it at WARNING regardless.
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    handler: Callable[[argparse.Namespace], int] = args.func
    return handler(args)
