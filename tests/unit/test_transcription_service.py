"""Unit tests for :mod:`radio_transforma.transcription.service`."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from radio_transforma.transcription import service as service_module
from radio_transforma.transcription.service import (
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL_NAME,
    TranscriptionService,
    TranscriptionServiceError,
)

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _raw(
    start: float = 0.0,
    end: float = 1.0,
    text: str = " olá",
    avg_logprob: float | None = -0.5,
) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text, avg_logprob=avg_logprob)


def _model(*segments: SimpleNamespace, language: str = "pt-PT") -> MagicMock:
    """Fake WhisperModel whose .transcribe() returns a fresh iterator each call."""
    model = MagicMock(name="whisper_model")
    model.transcribe.side_effect = lambda *args, **kwargs: (
        iter(segments),
        SimpleNamespace(language=language, duration=1.0),
    )
    return model


@pytest.fixture()
def audio_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.mp3"
    path.write_bytes(b"fake-audio")
    return path


# --------------------------------------------------------------------------- #
# Happy path                                                                  #
# --------------------------------------------------------------------------- #


def test_transcribe_builds_transcript_from_segments(audio_file: Path) -> None:
    model = _model(_raw(text=" olá"), _raw(start=1.0, end=2.0, text=" mundo"))
    factory = MagicMock(return_value=model)
    service = TranscriptionService(model_factory=factory)

    result = service.transcribe("a-1", audio_file)

    assert result.audio_id == "a-1"
    assert result.language == DEFAULT_LANGUAGE
    assert result.model == DEFAULT_MODEL_NAME
    assert result.wer is None
    assert len(result.segments) == 2
    assert result.segments[0].text == "olá"
    assert result.segments[1].text == "mundo"
    factory.assert_called_once_with()
    model.transcribe.assert_called_once_with(str(audio_file), language=DEFAULT_LANGUAGE)


def test_transcribe_passes_provided_language(audio_file: Path) -> None:
    model = _model(_raw())
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file, language="en")

    assert result.language == "en"
    model.transcribe.assert_called_once_with(str(audio_file), language="en")


def test_transcribe_uses_default_language(audio_file: Path) -> None:
    model = _model(_raw())
    service = TranscriptionService(model_factory=MagicMock(return_value=model))
    result = service.transcribe("a-1", audio_file)
    assert result.language == DEFAULT_LANGUAGE


def test_transcribe_trims_segment_text(audio_file: Path) -> None:
    model = _model(_raw(text="   com espaços   "))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert result.segments[0].text == "com espaços"


# --------------------------------------------------------------------------- #
# Lazy loading & reuse                                                        #
# --------------------------------------------------------------------------- #


def test_model_is_not_loaded_on_init(audio_file: Path) -> None:
    factory = MagicMock()
    TranscriptionService(model_factory=factory)
    factory.assert_not_called()


def test_model_is_reused_across_calls(audio_file: Path) -> None:
    model = _model(_raw())
    factory = MagicMock(return_value=model)
    service = TranscriptionService(model_factory=factory)

    service.transcribe("a-1", audio_file)
    service.transcribe("a-2", audio_file)

    factory.assert_called_once_with()


def test_model_load_failure_is_wrapped(audio_file: Path) -> None:
    factory = MagicMock(side_effect=RuntimeError("gpu exploded"))
    service = TranscriptionService(model_factory=factory)

    with pytest.raises(TranscriptionServiceError, match="gpu exploded"):
        service.transcribe("a-1", audio_file)


def test_default_model_factory_imports_faster_whisper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_model_cls = MagicMock(name="WhisperModel")
    fake_module = SimpleNamespace(WhisperModel=fake_model_cls)
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    result = service_module._default_model_factory()

    fake_model_cls.assert_called_once_with(DEFAULT_MODEL_NAME, device="auto", compute_type="int8")
    assert result is fake_model_cls.return_value


# --------------------------------------------------------------------------- #
# Failure modes                                                               #
# --------------------------------------------------------------------------- #


def test_transcribe_wraps_model_error(audio_file: Path) -> None:
    model = _model(_raw())
    model.transcribe.side_effect = RuntimeError("model boom")
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    with pytest.raises(TranscriptionServiceError, match="model boom"):
        service.transcribe("a-1", audio_file)


def test_transcribe_missing_file_raises(tmp_path: Path) -> None:
    service = TranscriptionService(model_factory=MagicMock())
    with pytest.raises(TranscriptionServiceError, match="audio file not found"):
        service.transcribe("a-1", tmp_path / "nope.mp3")


def test_transcribe_empty_segments_raises(audio_file: Path) -> None:
    model = _model()  # zero segments
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    with pytest.raises(TranscriptionServiceError, match="no segments"):
        service.transcribe("a-1", audio_file)


def test_transcribe_all_blank_text_raises(audio_file: Path) -> None:
    model = _model(_raw(text="   "), _raw(text=""))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    with pytest.raises(TranscriptionServiceError, match="no segments"):
        service.transcribe("a-1", audio_file)


def test_transcribe_skips_blank_text_segments(audio_file: Path) -> None:
    model = _model(_raw(text="   "), _raw(start=1.0, end=2.0, text=" boa"))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert len(result.segments) == 1
    assert result.segments[0].text == "boa"


# --------------------------------------------------------------------------- #
# Confidence                                                                  #
# --------------------------------------------------------------------------- #


def test_confidence_is_exp_of_avg_logprob(audio_file: Path) -> None:
    model = _model(_raw(avg_logprob=-1.0))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert result.segments[0].confidence == pytest.approx(math.exp(-1.0))


def test_confidence_clips_above_one(audio_file: Path) -> None:
    model = _model(_raw(avg_logprob=10.0))  # exp(10) ~ 22026
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert result.segments[0].confidence == 1.0


def test_confidence_none_when_avg_logprob_missing(audio_file: Path) -> None:
    model = _model(_raw(avg_logprob=None))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert result.segments[0].confidence is None


# --------------------------------------------------------------------------- #
# IDs & timestamps                                                            #
# --------------------------------------------------------------------------- #


def test_transcript_and_segment_ids_are_unique(audio_file: Path) -> None:
    model = _model(_raw(), _raw(start=1.0, end=2.0))
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    t1 = service.transcribe("a-1", audio_file)
    t2 = service.transcribe("a-1", audio_file)

    assert t1.id != t2.id
    assert t1.segments[0].id != t1.segments[1].id
    assert t1.segments[0].id != t2.segments[0].id


def test_transcript_created_at_has_timezone(audio_file: Path) -> None:
    model = _model(_raw())
    service = TranscriptionService(model_factory=MagicMock(return_value=model))

    result = service.transcribe("a-1", audio_file)

    assert result.created_at.tzinfo is not None


# --------------------------------------------------------------------------- #
# Argument validation                                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad_id", ["", "   ", None, 123])
def test_transcribe_rejects_invalid_audio_id(audio_file: Path, bad_id: object) -> None:
    service = TranscriptionService(model_factory=MagicMock())
    with pytest.raises(ValueError):
        service.transcribe(bad_id, audio_file)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_lang", ["", "   ", None, 123])
def test_transcribe_rejects_invalid_language(audio_file: Path, bad_lang: object) -> None:
    service = TranscriptionService(model_factory=MagicMock())
    with pytest.raises(ValueError):
        service.transcribe("a-1", audio_file, language=bad_lang)  # type: ignore[arg-type]


def test_transcribe_rejects_non_path() -> None:
    service = TranscriptionService(model_factory=MagicMock())
    with pytest.raises(TypeError):
        service.transcribe("a-1", "not/a/path")  # type: ignore[arg-type]
