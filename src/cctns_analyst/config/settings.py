"""Pydantic-settings — `Settings` with `env_prefix="APP_"`.

Secrets are stored as `SecretStr`. They are read by presence only — accessor
code in `cctns_analyst.llm.providers.gemini` unwraps the value at the moment
of use and never logs it.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # .env may contain unrelated variables; pydantic must not fail
    )

    # --- DB / mirror --------------------------------------------------------
    database_url: str = Field(default="sqlite:///./data/agent.db")
    cctns_mirror_url: str = Field(default="")
    gemini_api_key: SecretStr = Field(default=SecretStr(""))

    # --- Defaults overridable per-request via env ---------------------------
    llm_provider: str = Field(default="gemini")
    llm_model: str = Field(default="gemini-2.5-flash")

    # Mirror executor caps (defaults).
    row_cap: int = Field(default=1000, ge=1, le=10_000)
    statement_timeout_ms: int = Field(default=10_000, ge=100, le=60_000)

    # --- Observability ------------------------------------------------------
    log_level: str = Field(default="INFO")

    # --- Server -------------------------------------------------------------
    port: int = Field(default=8001)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached singleton. Tests call `_reset_settings()` to drop the cache."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _reset_settings() -> None:
    """Test-only — drop the cached Settings so env patches take effect."""
    global _settings
    _settings = None
