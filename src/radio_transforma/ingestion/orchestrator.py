"""End-to-end ingestion: local audio file → persisted Transcript.

Composes AudioRepository, TranscriptionService and TranscriptRepository into
one idempotent operation. This is the Phase 1 walking skeleton — the first
flow that does real work end-to-end.

Idempotency: calling :meth:`IngestionOrchestrator.ingest` twice with the same
``audio_id`` + ``language`` + transcriber model returns the same Transcript
without re-doing upload or transcription.

Partial failure: if a stage fails, the orchestrator raises
:class:`IngestionError` with ``.stage`` set to the failing stage. No
automatic retry, no cleanup. On retry, the idempotency check skips completed
work; only re-transcription after a persist failure is repeated.

Out of scope: audio download (caller provides a local Path), Modal wrapper
(Block 6), Langfuse tracing (Block 7).
"""

from __future__ import annotations

from pathlib import Path

from radio_transforma.models.transcript import Transcript
from radio_transforma.storage.audio_repository import (
    AudioRepository,
    AudioRepositoryError,
)
from radio_transforma.storage.transcript_repository import (
    TranscriptRepository,
    TranscriptRepositoryError,
)
from radio_transforma.transcription.service import (
    DEFAULT_LANGUAGE,
    TranscriptionService,
    TranscriptionServiceError,
)

_STORAGE_PREFIX = "audio"
_CONTENT_TYPES: dict[str, str] = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
_DEFAULT_CONTENT_TYPE = "application/octet-stream"


class IngestionError(RuntimeError):
    """Raised when ingestion fails, carrying the failing stage.

    Attributes:
        stage: one of ``validate``, ``idempotency``, ``upload``,
            ``transcribe``, ``persist``.
        audio_id: the audio identifier the orchestrator was working on.
    """

    def __init__(self, stage: str, audio_id: str, detail: str) -> None:
        super().__init__(f"[{stage}] {audio_id}: {detail}")
        self.stage = stage
        self.audio_id = audio_id


class IngestionOrchestrator:
    """Compose storage, transcription and persistence into one flow."""

    def __init__(
        self,
        audio_repo: AudioRepository,
        transcriber: TranscriptionService,
        transcripts: TranscriptRepository,
    ) -> None:
        self._audio_repo = audio_repo
        self._transcriber = transcriber
        self._transcripts = transcripts

    def ingest(
        self,
        audio_id: str,
        local_path: Path,
        *,
        language: str = DEFAULT_LANGUAGE,
    ) -> Transcript:
        """Take a local audio file through upload → transcribe → persist.

        Returns the persisted Transcript. Safe to call more than once for
        the same ``audio_id``/``language``/model combination.
        """
        self._validate(audio_id, local_path, language)

        if not local_path.is_file():
            raise IngestionError("validate", audio_id, f"file not found: {local_path}")

        existing = self._find_complete(audio_id, language)
        if existing is not None:
            return existing

        self._upload_if_needed(audio_id, local_path)
        transcript = self._transcribe(audio_id, local_path, language)
        self._persist(transcript, audio_id)
        return transcript

    # ------------------------------------------------------------------ #
    # Stages                                                             #
    # ------------------------------------------------------------------ #

    def _upload_if_needed(self, audio_id: str, local_path: Path) -> None:
        remote_path = self._remote_path(audio_id, local_path)
        try:
            if self._audio_repo.exists(remote_path):
                return
            self._audio_repo.upload(
                remote_path,
                local_path.read_bytes(),
                content_type=self._content_type(local_path),
            )
        except AudioRepositoryError as exc:
            raise IngestionError("upload", audio_id, str(exc)) from exc
        except OSError as exc:
            raise IngestionError("upload", audio_id, f"failed to read file: {exc}") from exc

    def _transcribe(self, audio_id: str, local_path: Path, language: str) -> Transcript:
        try:
            return self._transcriber.transcribe(audio_id, local_path, language=language)
        except TranscriptionServiceError as exc:
            raise IngestionError("transcribe", audio_id, str(exc)) from exc

    def _persist(self, transcript: Transcript, audio_id: str) -> None:
        try:
            self._transcripts.save(transcript)
        except TranscriptRepositoryError as exc:
            raise IngestionError("persist", audio_id, str(exc)) from exc

    # ------------------------------------------------------------------ #
    # Idempotency                                                        #
    # ------------------------------------------------------------------ #

    def _find_complete(self, audio_id: str, language: str) -> Transcript | None:
        """Return an existing complete transcript, or None.

        "Complete" means: matching language, matching model, non-empty
        segments. Orphan transcripts (0 segments from a failed partial save)
        are ignored and will be re-created.
        """
        try:
            candidates = self._transcripts.list_for_audio(audio_id)
        except TranscriptRepositoryError as exc:
            raise IngestionError("idempotency", audio_id, str(exc)) from exc

        for candidate in candidates:
            if (
                candidate.language == language
                and candidate.model == self._transcriber.model_name
                and candidate.segments
            ):
                return candidate
        return None

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _remote_path(audio_id: str, local_path: Path) -> str:
        return f"{_STORAGE_PREFIX}/{audio_id}{local_path.suffix.lower()}"

    @staticmethod
    def _content_type(local_path: Path) -> str:
        return _CONTENT_TYPES.get(local_path.suffix.lower(), _DEFAULT_CONTENT_TYPE)

    @staticmethod
    def _validate(audio_id: str, local_path: Path, language: str) -> None:
        if not isinstance(audio_id, str) or not audio_id.strip():
            raise ValueError("audio_id must be a non-empty string")
        if not isinstance(local_path, Path):
            raise TypeError("local_path must be a pathlib.Path")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
