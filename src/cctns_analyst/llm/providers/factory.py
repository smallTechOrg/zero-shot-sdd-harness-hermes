"""LLM provider factory — picks the real provider for the configured env."""

from __future__ import annotations

from cctns_analyst.config.settings import Settings
from cctns_analyst.llm.providers.base import LLMProvider


def create_provider(settings: Settings) -> LLMProvider:
    """Return the provider for ``settings``.

    Phase 1 supports Gemini only; Phase 3 will add an Anthropic provider
    using the existing factory plumbing. If no provider recognises the
    configuration we raise — that's the right behaviour: a misconfigured
    environment should fail loud, not silently swap to a stub.
    """
    provider = (settings.llm_provider or "gemini").strip().lower()
    if provider == "gemini":
        from cctns_analyst.llm.providers.gemini import GeminiProvider
        return GeminiProvider(settings)
    raise ValueError(f"unknown LLM provider: {provider!r}")
