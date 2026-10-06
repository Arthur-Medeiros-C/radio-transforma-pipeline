"""Transcript persistence in Postgres (Supabase).

Scope: CRUD for :class:`~radio_transforma.models.transcript.Transcript` and
its segments against two tables (``transcripts`` + ``transcript_segments``).
No embedding generation (Phase 2), no audio blobs (AudioRepository), no
transcription logic (TranscriptionService).
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from radio_transforma.models.transcript import Transcript, TranscriptSegment

if TYPE_CHECKING:
    from supabase import Client


_TRANSCRIPT_TABLE = "transcripts"
_SEGMENT_TABLE = "transcript_segments"


class TranscriptRepositoryError(RuntimeError):
    """Raised when a transcript persistence operation fails."""


class TranscriptRepository:
    """Read/write transcripts against Supabase Postgres."""

    def __init__(self, client: Client) -> None:
        self._client = client

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def save(self, transcript: Transcript) -> str:
        """Insert ``transcript`` and its segments. Returns the transcript id."""
        row = self._to_transcript_row(transcript)
        try:
            self._client.table(_TRANSCRIPT_TABLE).insert(row).execute()
        except Exception as exc:  # noqa: BLE001 — re-raised as domain error
            raise TranscriptRepositoryError(
                f"failed to insert transcript {row['id']!r}: {exc}"
            ) from exc

        if not transcript.segments:
            return transcript.id

        segment_rows = [
            self._to_segment_row(transcript.id, position, segment)
            for position, segment in enumerate(transcript.segments)
        ]
        try:
            self._client.table(_SEGMENT_TABLE).insert(segment_rows).execute()
        except Exception as exc:  # noqa: BLE001
            # Best-effort rollback: supabase-py has no cross-request tx.
            with contextlib.suppress(Exception):
                (self._client.table(_TRANSCRIPT_TABLE).delete().eq("id", transcript.id).execute())
            raise TranscriptRepositoryError(
                f"failed to insert segments for transcript {transcript.id!r}: {exc}"
            ) from exc

        return transcript.id

    def get(self, transcript_id: str) -> Transcript | None:
        """Return the transcript with ``transcript_id``, or ``None``."""
        self._validate_id(transcript_id)
        try:
            response = (
                self._client.table(_TRANSCRIPT_TABLE).select("*").eq("id", transcript_id).execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscriptRepositoryError(
                f"failed to fetch transcript {transcript_id!r}: {exc}"
            ) from exc

        rows = self._data(response)
        if not rows:
            return None
        return self._hydrate(rows[0])

    def list_for_audio(self, audio_id: str) -> list[Transcript]:
        """Return all transcripts attached to ``audio_id``, oldest first."""
        self._validate_id(audio_id)
        try:
            response = (
                self._client.table(_TRANSCRIPT_TABLE)
                .select("*")
                .eq("audio_id", audio_id)
                .order("created_at")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscriptRepositoryError(
                f"failed to list transcripts for audio {audio_id!r}: {exc}"
            ) from exc

        return [self._hydrate(row) for row in self._data(response)]

    def delete(self, transcript_id: str) -> None:
        """Delete the transcript and (via FK cascade) its segments."""
        self._validate_id(transcript_id)
        try:
            (self._client.table(_TRANSCRIPT_TABLE).delete().eq("id", transcript_id).execute())
        except Exception as exc:  # noqa: BLE001
            raise TranscriptRepositoryError(
                f"failed to delete transcript {transcript_id!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Row <-> model mapping                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_transcript_row(transcript: Transcript) -> dict[str, Any]:
        return {
            "id": transcript.id,
            "audio_id": transcript.audio_id,
            "language": transcript.language,
            "model": transcript.model,
            "wer": transcript.wer,
            "created_at": transcript.created_at.isoformat(),
        }

    @staticmethod
    def _to_segment_row(
        transcript_id: str, position: int, segment: TranscriptSegment
    ) -> dict[str, Any]:
        return {
            "id": segment.id,
            "transcript_id": transcript_id,
            "position": position,
            "start_s": segment.start,
            "end_s": segment.end,
            "text": segment.text,
            "confidence": segment.confidence,
        }

    def _hydrate(self, row: dict[str, Any]) -> Transcript:
        segments = self._fetch_segments(row["id"])
        return Transcript(
            id=row["id"],
            audio_id=row["audio_id"],
            language=row["language"],
            model=row["model"],
            wer=row.get("wer"),
            created_at=row["created_at"],
            segments=tuple(segments),
        )

    def _fetch_segments(self, transcript_id: str) -> list[TranscriptSegment]:
        try:
            response = (
                self._client.table(_SEGMENT_TABLE)
                .select("*")
                .eq("transcript_id", transcript_id)
                .order("position")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscriptRepositoryError(
                f"failed to fetch segments for transcript {transcript_id!r}: {exc}"
            ) from exc

        return [self._to_segment_model(row) for row in self._data(response)]

    @staticmethod
    def _to_segment_model(row: dict[str, Any]) -> TranscriptSegment:
        return TranscriptSegment(
            id=row["id"],
            start=row["start_s"],
            end=row["end_s"],
            text=row["text"],
            confidence=row.get("confidence"),
        )

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _data(response: Any) -> list[dict[str, Any]]:
        data = getattr(response, "data", None)
        if data is None and isinstance(response, dict):
            data = response.get("data")
        if data is None:
            return []
        return list(data)

    @staticmethod
    def _validate_id(value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("id must be a non-empty string")
