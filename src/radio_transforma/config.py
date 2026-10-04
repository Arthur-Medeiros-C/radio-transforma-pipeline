"""Centralised configuration for the Radio Transforma pipeline.

All environment-driven settings are defined here, validated by Pydantic.
No module should read `os.environ` directly — everything flows through this
configuration object.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are read from a `.env` file (see `.env.example`) or from the
    process environment. Field names are case-insensitive.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- LLM Providers ---
    openrouter_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="API key for OpenRouter (remote LLM inference).",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for a local Ollama server.",
    )

    # --- Supabase ---
    supabase_url: str = Field(
        default="",
        description="Supabase project URL.",
    )
    supabase_anon_key: SecretStr = Field(
        default=SecretStr(""),
        description="Supabase anon key (public, read-only scoped).",
    )
    supabase_service_role_key: SecretStr = Field(
        default=SecretStr(""),
        description="Supabase service role key (admin, never expose).",
    )

    # --- Observability ---
    langfuse_public_key: SecretStr = Field(default=SecretStr(""))
    langfuse_secret_key: SecretStr = Field(default=SecretStr(""))
    langfuse_host: str = Field(default="https://cloud.langfuse.com")

    # --- Modal ---
    modal_token_id: SecretStr = Field(default=SecretStr(""))
    modal_token_secret: SecretStr = Field(default=SecretStr(""))

    # --- n8n ---
    n8n_webhook_url: str = Field(default="")
    n8n_api_key: SecretStr = Field(default=SecretStr(""))

    # --- Derived properties ---
    @property
    def is_production(self) -> bool:
        """True when running in a production environment."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """True when running in a development environment."""
        return self.env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using `lru_cache` ensures the `.env` file is read only once per process,
    which is both faster and avoids subtle bugs when the file changes at
    runtime (which it never should).
    """
    return Settings()
