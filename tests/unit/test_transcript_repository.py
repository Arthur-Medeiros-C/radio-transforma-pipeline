"""Unit tests for :mod:`radio_transforma.storage.transcript_repository`."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from radio_transforma.models.transcript import Transcript, TranscriptSegment
from radio_transforma.storage.transcript_repository import (
    TranscriptRepository,
    TranscriptRepositoryError,
)

# --------------------------------------------------------------------------- #
# Fixtures & helpers                                                          #
# --------------------------------------------------------------------------- #


def _segment(
    segment_id: str = "s-1",
    start: float = 0.0,
    end: float = 1.0,
    text: str = "olá",
    confidence: float | None = 0.9,
) -> TranscriptSegment:
    return TranscriptSegment(
        id=segment_id,
        start=start,
        end=end,
        text=text,
        confidence=confidence,
    )


def _transcript(
    segments: tuple[TranscriptSegment, ...] = (),
    **overrides: object,
) -> Transcript:
    defaults: dict[str, object] = {
        "id": "t-1",
        "audio_id": "a-1",
        "language": "pt-PT",
        "model": "large-v3",
        "wer": None,
        "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        "segments": segments,
    }
    defaults.update(overrides)
    return Transcript(**defaults)  # type: ignore[arg-type]


def _make_table(name: str, data: list[dict[str, object]]) -> MagicMock:
    table = MagicMock(name=f"table:{name}")
    table.select.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.insert.return_value = table
    table.delete.return_value = table
    table.execute.return_value = MagicMock(data=data)
    return table


def _setup_tables(
    client: MagicMock, responses: dict[str, list[dict[str, object]]]
) -> dict[str, MagicMock]:
    """Pre-create both tables so tests can configure side_effects up front."""
    tables = {
        "transcripts": _make_table("transcripts", responses.get("transcripts", [])),
        "transcript_segments": _make_table(
            "transcript_segments", responses.get("transcript_segments", [])
        ),
    }
    client.table.side_effect = lambda name: tables[name]
    return tables


@pytest.fixture()
def client() -> MagicMock:
    return MagicMock(name="supabase_client")


@pytest.fixture()
def repo(client: MagicMock) -> TranscriptRepository:
    return TranscriptRepository(client)


# --------------------------------------------------------------------------- #
# save                                                                        #
# --------------------------------------------------------------------------- #


def test_save_without_segments_inserts_only_transcript(
    repo: TranscriptRepository, client: MagicMock
) -> None:
    tables = _setup_tables(client, {})
    result = repo.save(_transcript())

    assert result == "t-1"
    tables["transcripts"].insert.assert_called_once()
    tables["transcript_segments"].insert.assert_not_called()


def test_save_with_segments_inserts_transcript_then_batch(
    repo: TranscriptRepository, client: MagicMock
) -> None:
    tables = _setup_tables(client, {})
    payload = _transcript(
        segments=(
            _segment(segment_id="s-1"),
            _segment(segment_id="s-2", start=1.0, end=2.0),
        )
    )

    assert repo.save(payload) == "t-1"

    transcript_rows = tables["transcripts"].insert.call_args.args[0]
    assert transcript_rows["id"] == "t-1"
    assert transcript_rows["audio_id"] == "a-1"
    assert transcript_rows["language"] == "pt-PT"
    assert transcript_rows["model"] == "large-v3"
    assert transcript_rows["wer"] is None
    assert "created_at" in transcript_rows

    segment_rows = tables["transcript_segments"].insert.call_args.args[0]
    assert [r["position"] for r in segment_rows] == [0, 1]
    assert [r["id"] for r in segment_rows] == ["s-1", "s-2"]
    assert segment_rows[0]["transcript_id"] == "t-1"
    assert segment_rows[0]["start_s"] == 0.0
    assert segment_rows[0]["end_s"] == 1.0
    assert segment_rows[0]["text"] == "olá"
    assert segment_rows[0]["confidence"] == 0.9


def test_save_wraps_transcript_insert_error(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.side_effect = RuntimeError("pk violation")

    with pytest.raises(TranscriptRepositoryError, match="pk violation"):
        repo.save(_transcript())


def test_save_rolls_back_transcript_on_segment_failure(
    repo: TranscriptRepository, client: MagicMock
) -> None:
    tables = _setup_tables(client, {})
    tables["transcript_segments"].execute.side_effect = RuntimeError("segment boom")

    with pytest.raises(TranscriptRepositoryError, match="segment boom"):
        repo.save(_transcript(segments=(_segment(),)))

    tables["transcripts"].delete.assert_called_once()
    tables["transcripts"].eq.assert_called_with("id", "t-1")


def test_save_swallows_rollback_failure(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    tables["transcript_segments"].execute.side_effect = RuntimeError("segment boom")
    tables["transcripts"].delete.side_effect = RuntimeError("rollback boom")

    with pytest.raises(TranscriptRepositoryError, match="segment boom"):
        repo.save(_transcript(segments=(_segment(),)))


# --------------------------------------------------------------------------- #
# get                                                                         #
# --------------------------------------------------------------------------- #


def test_get_returns_none_when_missing(repo: TranscriptRepository, client: MagicMock) -> None:
    _setup_tables(client, {})
    assert repo.get("t-404") is None


def test_get_hydrates_transcript_with_segments(
    repo: TranscriptRepository, client: MagicMock
) -> None:
    transcript_row = {
        "id": "t-1",
        "audio_id": "a-1",
        "language": "pt-PT",
        "model": "large-v3",
        "wer": 0.12,
        "created_at": "2026-01-01T12:00:00+00:00",
    }
    segment_rows = [
        {
            "id": "s-1",
            "position": 0,
            "start_s": 0.0,
            "end_s": 1.5,
            "text": "bom dia",
            "confidence": 0.95,
        },
        {
            "id": "s-2",
            "position": 1,
            "start_s": 1.5,
            "end_s": 3.0,
            "text": "portugal",
            "confidence": None,
        },
    ]
    tables = _setup_tables(
        client,
        {"transcripts": [transcript_row], "transcript_segments": segment_rows},
    )

    result = repo.get("t-1")

    assert result is not None
    assert result.id == "t-1"
    assert result.audio_id == "a-1"
    assert result.wer == 0.12
    assert len(result.segments) == 2
    assert result.segments[0].id == "s-1"
    assert result.segments[0].text == "bom dia"
    assert result.segments[1].confidence is None
    tables["transcript_segments"].order.assert_called_with("position")


def test_get_wraps_transcript_fetch_error(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.side_effect = RuntimeError("network")

    with pytest.raises(TranscriptRepositoryError, match="network"):
        repo.get("t-1")


def test_get_wraps_segment_fetch_error(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(
        client,
        {
            "transcripts": [
                {
                    "id": "t-1",
                    "audio_id": "a-1",
                    "language": "pt-PT",
                    "model": "large-v3",
                    "wer": None,
                    "created_at": "2026-01-01T12:00:00+00:00",
                }
            ]
        },
    )
    tables["transcript_segments"].execute.side_effect = RuntimeError("segments down")

    with pytest.raises(TranscriptRepositoryError, match="segments down"):
        repo.get("t-1")


@pytest.mark.parametrize("bad_id", ["", "   ", None, 123])
def test_get_rejects_invalid_id(repo: TranscriptRepository, bad_id: object) -> None:
    with pytest.raises(ValueError):
        repo.get(bad_id)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# list_for_audio                                                              #
# --------------------------------------------------------------------------- #


def test_list_for_audio_returns_empty(repo: TranscriptRepository, client: MagicMock) -> None:
    _setup_tables(client, {})
    assert repo.list_for_audio("a-1") == []


def test_list_for_audio_hydrates_each(repo: TranscriptRepository, client: MagicMock) -> None:
    rows = [
        {
            "id": "t-1",
            "audio_id": "a-1",
            "language": "pt-PT",
            "model": "large-v3",
            "wer": None,
            "created_at": "2026-01-01T12:00:00+00:00",
        },
        {
            "id": "t-2",
            "audio_id": "a-1",
            "language": "pt-PT",
            "model": "medium",
            "wer": 0.3,
            "created_at": "2026-01-02T12:00:00+00:00",
        },
    ]
    tables = _setup_tables(client, {"transcripts": rows})

    result = repo.list_for_audio("a-1")

    assert [t.id for t in result] == ["t-1", "t-2"]
    tables["transcripts"].eq.assert_called_with("audio_id", "a-1")
    tables["transcripts"].order.assert_called_with("created_at")


def test_list_for_audio_wraps_errors(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.side_effect = RuntimeError("boom")

    with pytest.raises(TranscriptRepositoryError, match="boom"):
        repo.list_for_audio("a-1")


# --------------------------------------------------------------------------- #
# delete                                                                      #
# --------------------------------------------------------------------------- #


def test_delete_calls_delete_eq_execute(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    repo.delete("t-1")
    tables["transcripts"].delete.assert_called_once()
    tables["transcripts"].eq.assert_called_with("id", "t-1")


def test_delete_wraps_errors(repo: TranscriptRepository, client: MagicMock) -> None:
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.side_effect = RuntimeError("permission denied")

    with pytest.raises(TranscriptRepositoryError, match="permission denied"):
        repo.delete("t-1")


@pytest.mark.parametrize("bad_id", ["", "   ", None, 123])
def test_delete_rejects_invalid_id(repo: TranscriptRepository, bad_id: object) -> None:
    with pytest.raises(ValueError):
        repo.delete(bad_id)  # type: ignore[arg-type]


def test_get_handles_dict_response(repo: TranscriptRepository, client: MagicMock) -> None:
    """Supabase SDK has returned dicts in some versions; _data() must cope."""

    class _DictResponse(dict):
        pass

    transcript_dict = {
        "id": "t-1",
        "audio_id": "a-1",
        "language": "pt-PT",
        "model": "large-v3",
        "wer": None,
        "created_at": "2026-01-01T12:00:00+00:00",
    }
    segment_dict = {
        "id": "s-1",
        "position": 0,
        "start_s": 0.0,
        "end_s": 1.0,
        "text": "olá",
        "confidence": 0.9,
    }
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.return_value = _DictResponse(data=[transcript_dict])
    tables["transcript_segments"].execute.return_value = _DictResponse(data=[segment_dict])

    result = repo.get("t-1")

    assert result is not None
    assert result.id == "t-1"
    assert len(result.segments) == 1
    assert result.segments[0].id == "s-1"


def test_get_returns_none_when_response_has_no_data(
    repo: TranscriptRepository, client: MagicMock
) -> None:
    """Response without .data attr and not a dict → _data() returns []."""
    tables = _setup_tables(client, {})
    tables["transcripts"].execute.return_value = MagicMock(data=None)

    assert repo.get("t-1") is None
