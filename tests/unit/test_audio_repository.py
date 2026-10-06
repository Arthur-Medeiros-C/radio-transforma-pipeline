"""Unit tests for :mod:`radio_transforma.storage.audio_repository`."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from radio_transforma.storage.audio_repository import (
    AudioRepository,
    AudioRepositoryError,
)


@pytest.fixture()
def storage_sdk() -> MagicMock:
    """Mock for ``client.storage.from_(bucket)``."""
    return MagicMock(name="storage_bucket")


@pytest.fixture()
def repo(storage_sdk: MagicMock) -> AudioRepository:
    client = MagicMock(name="supabase_client")
    client.storage.from_.return_value = storage_sdk
    return AudioRepository(client)


# --------------------------------------------------------------------------- #
# Construction                                                                #
# --------------------------------------------------------------------------- #


def test_default_bucket_is_audio(storage_sdk: MagicMock) -> None:
    client = MagicMock()
    client.storage.from_.return_value = storage_sdk
    repo = AudioRepository(client)
    assert repo.bucket == "audio"


def test_custom_bucket_is_used(storage_sdk: MagicMock) -> None:
    client = MagicMock()
    client.storage.from_.return_value = storage_sdk
    repo = AudioRepository(client, bucket="interviews")
    repo.upload("a.mp3", b"x", content_type="audio/mpeg")
    client.storage.from_.assert_called_with("interviews")


@pytest.mark.parametrize("bucket", ["", "   ", None, 123])
def test_invalid_bucket_rejected(bucket: object) -> None:
    with pytest.raises(ValueError):
        AudioRepository(MagicMock(), bucket=bucket)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# upload                                                                      #
# --------------------------------------------------------------------------- #


def test_upload_sends_content_type_and_returns_path(
    repo: AudioRepository, storage_sdk: MagicMock
) -> None:
    result = repo.upload("2026/ep01.mp3", b"\x00\x01", content_type="audio/mpeg")

    assert result == "2026/ep01.mp3"
    storage_sdk.upload.assert_called_once_with(
        "2026/ep01.mp3",
        b"\x00\x01",
        file_options={"content-type": "audio/mpeg", "upsert": "false"},
    )


def test_upload_wraps_sdk_errors(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.upload.side_effect = RuntimeError("bucket offline")

    with pytest.raises(AudioRepositoryError, match="bucket offline"):
        repo.upload("a.mp3", b"x", content_type="audio/mpeg")


def test_upload_rejects_non_bytes_payload(repo: AudioRepository) -> None:
    with pytest.raises(TypeError):
        repo.upload("a.mp3", "not-bytes", content_type="audio/mpeg")  # type: ignore[arg-type]


def test_upload_rejects_empty_content_type(repo: AudioRepository) -> None:
    with pytest.raises(ValueError):
        repo.upload("a.mp3", b"x", content_type="")


# --------------------------------------------------------------------------- #
# download                                                                    #
# --------------------------------------------------------------------------- #


def test_download_returns_bytes(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.download.return_value = b"payload"
    assert repo.download("a.mp3") == b"payload"


def test_download_normalises_bytearray(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.download.return_value = bytearray(b"payload")
    result = repo.download("a.mp3")
    assert result == b"payload"
    assert isinstance(result, bytes)


def test_download_wraps_sdk_errors(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.download.side_effect = RuntimeError("not found")
    with pytest.raises(AudioRepositoryError, match="not found"):
        repo.download("a.mp3")


def test_download_rejects_unexpected_payload(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.download.return_value = {"oops": True}
    with pytest.raises(AudioRepositoryError, match="unexpected download payload"):
        repo.download("a.mp3")


# --------------------------------------------------------------------------- #
# create_signed_url                                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", ["signedURL", "signed_url", "signedUrl"])
def test_create_signed_url_accepts_known_keys(
    repo: AudioRepository, storage_sdk: MagicMock, key: str
) -> None:
    storage_sdk.create_signed_url.return_value = {key: "https://example/sig"}
    assert repo.create_signed_url("a.mp3") == "https://example/sig"
    storage_sdk.create_signed_url.assert_called_once_with("a.mp3", 3600)


def test_create_signed_url_custom_ttl(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.create_signed_url.return_value = {"signedURL": "u"}
    repo.create_signed_url("a.mp3", expires_in=120)
    storage_sdk.create_signed_url.assert_called_once_with("a.mp3", 120)


def test_create_signed_url_missing_key_raises(
    repo: AudioRepository, storage_sdk: MagicMock
) -> None:
    storage_sdk.create_signed_url.return_value = {}
    with pytest.raises(AudioRepositoryError, match="signed URL missing"):
        repo.create_signed_url("a.mp3")


def test_create_signed_url_wraps_sdk_errors(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.create_signed_url.side_effect = RuntimeError("kaboom")
    with pytest.raises(AudioRepositoryError, match="kaboom"):
        repo.create_signed_url("a.mp3")


@pytest.mark.parametrize("ttl", [0, -1])
def test_create_signed_url_rejects_non_positive_ttl(repo: AudioRepository, ttl: int) -> None:
    with pytest.raises(ValueError):
        repo.create_signed_url("a.mp3", expires_in=ttl)


def test_create_signed_url_supports_object_response(
    repo: AudioRepository, storage_sdk: MagicMock
) -> None:
    class _Resp:
        signedURL = "https://example/obj"

    storage_sdk.create_signed_url.return_value = _Resp()
    assert repo.create_signed_url("a.mp3") == "https://example/obj"


def test_create_signed_url_object_response_without_url_raises(
    repo: AudioRepository, storage_sdk: MagicMock
) -> None:
    class _Resp:  # no attributes at all
        pass

    storage_sdk.create_signed_url.return_value = _Resp()
    with pytest.raises(AudioRepositoryError, match="signed URL missing"):
        repo.create_signed_url("a.mp3")


# --------------------------------------------------------------------------- #
# exists                                                                      #
# --------------------------------------------------------------------------- #


def test_exists_true_when_listed(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.list.return_value = [
        {"name": "other.mp3"},
        {"name": "ep01.mp3"},
    ]
    assert repo.exists("2026/ep01.mp3") is True
    storage_sdk.list.assert_called_once_with("2026")


def test_exists_false_when_not_listed(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.list.return_value = [{"name": "other.mp3"}]
    assert repo.exists("2026/ep01.mp3") is False


def test_exists_at_bucket_root_uses_empty_prefix(
    repo: AudioRepository, storage_sdk: MagicMock
) -> None:
    storage_sdk.list.return_value = [{"name": "ep01.mp3"}]
    assert repo.exists("ep01.mp3") is True
    storage_sdk.list.assert_called_once_with("")


def test_exists_tolerates_none_listing(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.list.return_value = None
    assert repo.exists("a.mp3") is False


def test_exists_wraps_sdk_errors(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.list.side_effect = RuntimeError("network")
    with pytest.raises(AudioRepositoryError, match="network"):
        repo.exists("a.mp3")


# --------------------------------------------------------------------------- #
# delete                                                                      #
# --------------------------------------------------------------------------- #


def test_delete_calls_remove_with_list(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    repo.delete("2026/ep01.mp3")
    storage_sdk.remove.assert_called_once_with(["2026/ep01.mp3"])


def test_delete_wraps_sdk_errors(repo: AudioRepository, storage_sdk: MagicMock) -> None:
    storage_sdk.remove.side_effect = RuntimeError("permission denied")
    with pytest.raises(AudioRepositoryError, match="permission denied"):
        repo.delete("a.mp3")


# --------------------------------------------------------------------------- #
# Path validation (shared)                                                    #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "bad_path",
    ["", "   ", "/leading.mp3", "a/../b.mp3", "../escape.mp3"],
)
def test_invalid_paths_rejected(repo: AudioRepository, bad_path: str) -> None:
    with pytest.raises(ValueError):
        repo.upload(bad_path, b"x", content_type="audio/mpeg")
    with pytest.raises(ValueError):
        repo.download(bad_path)
    with pytest.raises(ValueError):
        repo.create_signed_url(bad_path)
    with pytest.raises(ValueError):
        repo.exists(bad_path)
    with pytest.raises(ValueError):
        repo.delete(bad_path)
