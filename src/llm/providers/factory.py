"""Provider factory — resolves provider + model from settings.

``auto`` picks whichever key is set. With no key at all we raise a clear,
actionable error: the real provider is the default and the only gated path — there
is no silent stub fallback (harness/rules/ai-agents.md rule 7).
"""
from __future__ import annotations

from src.config.settings import get_settings
from src.llm.providers.anthropic import AnthropicProvider
from src.llm.providers.base import LLMError, LLMProvider
from src.llm.providers.gemini import GeminiProvider
from src.llm.providers.nim import NIMProvider
from src.llm.providers.openrouter import OpenRouterProvider


def create_llm_provider() -> LLMProvider:
 s = get_settings()
 provider = s.resolve_provider()
 model = s.resolve_model()

 if provider == "anthropic":
  return AnthropicProvider(api_key=s.anthropic_api_key, model=model)
 if provider == "gemini":
  return GeminiProvider(api_key=s.gemini_api_key, model=model)
 if provider == "nim":
  return NIMProvider(api_key=s.key_for("nim"), model=model, base_url=s.openai_base_url)
 if provider == "openrouter":
  return OpenRouterProvider(
   api_key=s.openrouter_api_key, model=model, base_url=s.openrouter_base_url
  )
 raise LLMError(
  "No LLM API key configured. Set one of AGENT_ANTHROPIC_API_KEY, "
  "AGENT_GEMINI_API_KEY, AGENT_OPENROUTER_API_KEY, OPENAI_API_KEY, or "
  "OPENAI_COMPAT_API_KEY in .env (see .env.example)."
 )
