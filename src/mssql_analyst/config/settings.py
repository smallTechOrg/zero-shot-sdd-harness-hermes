"""Pydantic-settings — `Settings` with `env_prefix=\"AGENT_\"`.

Secrets are stored as ``SecretStr``. They are read by ``get_secret_value()``
at the moment of use in the provider module; never logged, never echoed.
"""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # .env may contain unrelated variables
    )

    # ---- audit DB (SQLite) --------------------------------------------------
    database_url: str = Field(default="sqlite:///./data/agent.db")

    # ---- LLM provider (Gemini primary) -------------------------------------
    llm_provider: str = Field(default="gemini")
    # Verified against the live ListModels whitelist on this account.
    # Default is `gemini-3.1-pro-preview` (no bare `gemini-3.1-pro` exists).
    # Override via AGENT_LLM_MODEL in .env if you want a different one.
    llm_model: str = Field(default="gemini-3.1-pro-preview")
    gemini_api_key: SecretStr = Field(default=SecretStr(""))

    # ---- MSSQL source (live, Windows Integrated Auth) -----------------------
    mssql_host: str = Field(default="")
    mssql_db: str = Field(default="master")
    mssql_driver: str = Field(default="ODBC Driver 17 for SQL Server")
    mssql_integrated_auth: bool = Field(default=True)
    mssql_user: str = Field(default="")
    mssql_password: SecretStr = Field(default=SecretStr(""))
    mssql_query_timeout_sec: int = Field(default=15, ge=1, le=120)
    mssql_row_cap: int = Field(default=1000, ge=1, le=10_000)

    # ---- Observability ------------------------------------------------------
    log_level: str = Field(default="INFO")

    # ---- Server -------------------------------------------------------------
    port: int = Field(default=8001)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached singleton. Tests call ``_reset_settings()`` to drop it."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def _reset_settings() -> None:
    """Test-only — drop the cached settings so env patches take effect."""
    global _settings
    _settings = None
