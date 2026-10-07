"""Null Object implementations for dry-run mode.

Used by the CLI (``--dry-run``) and, later, by the Modal wrapper. Each class
mirrors the documented public interface of its real counterpart but performs
no side effects: no network, no GPU, no database writes.

Signature note: ``AudioRepository`` and ``TranscriptRepository`` methods use
``*args, **kwargs`` because their exact signatures are not formally declared
via ``typing.Protocol``. ``NullTranscriptionService`` mirrors the documented
signature from the state document, since it is the only one with an enforced
contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from radio_transforma.models.transcript import Transcript, TranscriptSegment


class NullAudioRepository:
    """No-op ``AudioRepository``: never touches Supabase Storage."""

    def upload(self, *args: Any, **kwargs: Any) -> str:
        return "dry-run://audio"

    def download(self, *args: Any, **kwargs: Any) -> bytes:
        return b""

    def create_signed_url(self, *args: Any, **kwargs: Any) -> str:
        return "dry-run://signed"

    def exists(self, *args: Any, **kwargs: Any) -> bool:
        # Force the orchestrator to exercise the upload branch.
        return False

    def delete(self, *args: Any, **kwargs: Any) -> None:
        return None


class NullTranscriptRepository:
    """No-op ``TranscriptRepository``: never touches Postgres."""

    def save(self, *args: Any, **kwargs: Any) -> None:
        return None

    def get(self, *args: Any, **kwargs: Any) -> None:
        # Force the orchestrator to exercise the transcribe+persist branch.
        return None

    def list_for_audio(self, *args: Any, **kwargs: Any) -> list[Transcript]:
        return []

    def delete(self, *args: Any, **kwargs: Any) -> None:
        return None


class NullTranscriptionService:
    """``TranscriptionService`` substitute that skips GPU inference.

    Still validates that ``audio_path`` exists — a cheap input check that
    catches configuration errors before a real run would burn GPU credits.
    """

    model_name: str = "dry-run"

    def transcribe(
        self,
        audio_id: str,
        audio_path: Path,
        *,
        language: str = "pt-PT",
    ) -> Transcript:
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"dry-run: audio file not found: {audio_path}")
        return Transcript(
            id=f"dry-run-{audio_id}",
            audio_id=audio_id,
            language=language,
            model=self.model_name,
            created_at=datetime.now(UTC),
            segments=(
                TranscriptSegment(
                    id=f"dry-run-{audio_id}-0",
                    start=0.0,
                    end=1.0,
                    text="[dry-run segment]",
                ),
            ),
        )
