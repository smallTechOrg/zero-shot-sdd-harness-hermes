"""LLM provider factory — picks the real provider for the configured env."""

from __future__ import annotations

from mssql_analyst.config.settings import Settings
from mssql_analyst.llm.providers.base import LLMProvider


def create_provider(settings: Settings) -> LLMProvider:
    """Return the provider for ``settings``.

    Phase 1 supports Gemini only. If no provider recognises the configuration
    we raise — a misconfigured environment should fail loud, NOT silently
    default to a stub.
    """
    provider = (settings.llm_provider or "gemini").strip().lower()
    if provider == "gemini":
        from mssql_analyst.llm.providers.gemini import GeminiProvider

        return GeminiProvider(settings)
    raise ValueError(f"unknown LLM provider: {provider!r}")
