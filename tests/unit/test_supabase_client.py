"""Testes do cliente Supabase — puramente com mocks, zero rede."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from radio_transforma.storage.supabase_client import (
    SupabaseClientError,
    get_supabase_client,
    reset_supabase_client,
)


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    """Garante que o lru_cache não vaza entre testes."""
    reset_supabase_client()
    yield
    reset_supabase_client()


class _FakeSettings:
    """Stand-in tipado para `Settings` — só os campos que o cliente lê."""

    def __init__(
        self,
        *,
        url: str = "https://x.supabase.co",
        anon: str = "",
        service: str = "",
    ) -> None:
        self.supabase_url = url
        self.supabase_anon_key = SecretStr(anon)
        self.supabase_service_role_key = SecretStr(service)


def _patch_settings(fake: _FakeSettings):
    return patch(
        "radio_transforma.storage.supabase_client.get_settings",
        return_value=fake,
    )


def test_raises_when_url_missing() -> None:
    with (
        _patch_settings(_FakeSettings(url="", anon="k")),
        pytest.raises(SupabaseClientError, match="SUPABASE_URL"),
    ):
        get_supabase_client()


def test_raises_when_no_key() -> None:
    with (
        _patch_settings(_FakeSettings(anon="", service="")),
        pytest.raises(SupabaseClientError, match="chave Supabase"),
    ):
        get_supabase_client()


def test_prefers_service_role_key() -> None:
    with (
        _patch_settings(_FakeSettings(anon="anon", service="service")),
        patch("radio_transforma.storage.supabase_client.create_client") as mock_create,
    ):
        mock_create.return_value = MagicMock()
        get_supabase_client()

    mock_create.assert_called_once_with("https://x.supabase.co", "service")


def test_falls_back_to_anon_key() -> None:
    with (
        _patch_settings(_FakeSettings(anon="anon", service="")),
        patch("radio_transforma.storage.supabase_client.create_client") as mock_create,
    ):
        mock_create.return_value = MagicMock()
        get_supabase_client()

    mock_create.assert_called_once_with("https://x.supabase.co", "anon")


def test_client_is_memoised() -> None:
    with (
        _patch_settings(_FakeSettings(service="service")),
        patch("radio_transforma.storage.supabase_client.create_client") as mock_create,
    ):
        sentinel = MagicMock(name="client")
        mock_create.return_value = sentinel

        first = get_supabase_client()
        second = get_supabase_client()

    assert first is second is sentinel
    mock_create.assert_called_once()


def test_create_client_failure_is_wrapped() -> None:
    with (
        _patch_settings(_FakeSettings(service="service")),
        patch(
            "radio_transforma.storage.supabase_client.create_client",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(SupabaseClientError, match="boom"),
    ):
        get_supabase_client()


def test_url_and_key_are_stripped() -> None:
    with (
        _patch_settings(_FakeSettings(url="  https://x.supabase.co  ", service="  service  ")),
        patch("radio_transforma.storage.supabase_client.create_client") as mock_create,
    ):
        mock_create.return_value = MagicMock()
        get_supabase_client()

    mock_create.assert_called_once_with("https://x.supabase.co", "service")
