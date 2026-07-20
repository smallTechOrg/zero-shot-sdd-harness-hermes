"""Application settings — Pydantic BaseSettings, env prefix ``AGENT_``."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-flash",
    "openrouter": "anthropic/claude-sonnet-4-6",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Paths
    data_dir: Path = Field(default=Path("./data"))

    # Database
    database_url: str = Field(default="sqlite:///./data/app.db")
    duckdb_dir: Path = Field(default=Path("./data/sessions"))

    # LLM
    llm_provider: str = Field(default="auto")
    llm_model: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")

    # CSV / session limits
    max_csv_bytes: int = Field(default=100 * 1024 * 1024)  # 100 MB
    max_sessions: int = Field(default=50)
    max_history_turns: int = Field(default=20)

    # Rate limiting
    rate_limit_runs_per_minute: int = Field(default=20)

    # Phase 2
    mssql_connection_string: str = Field(default="")
    cache_ttl_seconds: int = Field(default=3600)

    log_level: str = Field(default="INFO")

    # ----- derived -----
    def resolve_provider(self) -> str:
        p = (self.llm_provider or "auto").strip().lower()
        if p != "auto":
            return p
        if self.anthropic_api_key:
            return "anthropic"
        if self.gemini_api_key:
            return "gemini"
        if self.openrouter_api_key:
            return "openrouter"
        return "stub"

    def resolve_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        return DEFAULT_MODELS.get(self.resolve_provider(), "")

    def key_for(self, provider: str) -> str:
        return {
            "anthropic": self.anthropic_api_key,
            "gemini": self.gemini_api_key,
            "openrouter": self.openrouter_api_key,
        }.get(provider, "")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.data_dir.mkdir(parents=True, exist_ok=True)
        _settings.duckdb_dir.mkdir(parents=True, exist_ok=True)
    return _settings
