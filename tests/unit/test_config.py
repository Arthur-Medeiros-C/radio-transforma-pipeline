"""Tests for the centralised configuration.

These tests verify that `Settings` behaves correctly with respect to:
- default values (safe when .env is missing)
- environment overrides
- derived properties
- secret handling (no accidental leakage of sensitive values)
"""

import pytest
from pydantic import SecretStr

from radio_transforma.config import Settings, get_settings


class TestSettingsDefaults:
    """Verify the defaults are safe and predictable."""

    def test_default_environment_is_development(self) -> None:
        settings = Settings()
        assert settings.env == "development"
        assert settings.is_development is True
        assert settings.is_production is False

    def test_default_log_level_is_info(self) -> None:
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_default_ollama_url_is_localhost(self) -> None:
        settings = Settings()
        assert settings.ollama_base_url == "http://localhost:11434"

    def test_secrets_default_to_empty_but_are_secret(self) -> None:
        settings = Settings()
        assert isinstance(settings.openrouter_api_key, SecretStr)
        assert settings.openrouter_api_key.get_secret_value() == ""


class TestSettingsOverrides:
    """Verify that environment variables override the defaults."""

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENV", "production")
        settings = Settings()
        assert settings.env == "production"
        assert settings.is_production is True

    def test_log_level_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_openrouter_key_is_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-123")
        settings = Settings()
        assert isinstance(settings.openrouter_api_key, SecretStr)
        # Value must not leak in plain __repr__ or __str__
        assert "sk-or-test-123" not in repr(settings.openrouter_api_key)
        assert settings.openrouter_api_key.get_secret_value() == "sk-or-test-123"


class TestSettingsCache:
    """Verify the cached factory returns a singleton."""

    def test_get_settings_is_cached(self) -> None:
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second
        get_settings.cache_clear()