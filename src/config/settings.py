"""Application settings — Pydantic BaseSettings, env prefix ``AGENT_``.

The provider key is loaded from ``.env`` (the single manual user step). Presence
is checked by ``bool`` only — the value is never echoed, logged, or committed.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Provider defaults used when AGENT_LLM_MODEL is blank. Verify against current
# provider docs before pinning — a 404 from the LLM API usually means a stale name.
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-flash",
    "openrouter": "tencent/hy3",  # cheap default ($0.14/M in) — frontier models 402 on unfunded keys; override via AGENT_LLM_MODEL
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(default="sqlite:///./data/app.db")

    # "auto" resolves to whichever provider key is set.
    llm_provider: str = Field(default="auto")
    llm_model: str = Field(default="")

    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")

    log_level: str = Field(default="INFO")

    # ----- derived -----
    def resolve_provider(self) -> str:
        """The effective provider name, or ``"stub"`` when no key is present."""
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
    return _settings
