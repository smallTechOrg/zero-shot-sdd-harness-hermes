"""Application settings — Pydantic BaseSettings, env prefix ``AGENT_`` (and raw OpenAI-compatible vars).

The provider key is loaded from ``.env`` (the single manual user step). Presence
is checked by ``bool`` only — the value is never echoed, logged, or committed.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

# Provider defaults used when AGENT_LLM_MODEL is blank.
DEFAULT_MODELS = {
 "anthropic": "claude-sonnet-4-6",
 "gemini": "gemini-2.5-flash",
 "nim": "meta/llama-3-8b-instruct", # NVIDIA NIM OpenAI-compatible path
 "openrouter": "mistralai/mistral-7b-instruct:free", # OpenRouter free tier fallback
}


class Settings(BaseSettings):
 model_config = SettingsConfigDict(
  env_prefix="AGENT_",
  env_file=".env",
  case_sensitive=False,
  extra="ignore",
 )

 database_url: str = Field(default="sqlite:///./data/app.db")

 # --- provider selection ---
 llm_provider: str = Field(default="auto")
 llm_model: str = Field(default="")

 # --- legacy provider keys (still supported) ---
 anthropic_api_key: str = Field(default="")
 gemini_api_key: str = Field(default="")

 # --- OpenAI-compatible / NIM / OpenRouter path ---
 # Accept both AGENT_OPENAI_API_KEY and OPENAI_API_KEY for compatibility
 openai_api_key: str = Field(
  default="",
  validation_alias=AliasChoices("AGENT_OPENAI_API_KEY", "OPENAI_API_KEY"),
 )
 openai_base_url: str = Field(
  default="https://integrate.api.nvidia.com/v1",
  validation_alias=AliasChoices("AGENT_OPENAI_BASE_URL", "OPENAI_BASE_URL"),
 )
 openai_model: str = Field(
  default="",
  validation_alias=AliasChoices("AGENT_OPENAI_MODEL", "OPENAI_MODEL"),
 )

 log_level: str = Field(default="INFO")

 # --- OpenAI-compatible provider key alias ---
 # Accept both prefixed and unprefixed env vars for compatibility
 openai_compat_api_key: str = Field(
  default="",
  validation_alias=AliasChoices("AGENT_OPENAI_COMPAT_API_KEY", "OPENAI_COMPAT_API_KEY"),
 )

 # --- CSV / analyst options ---
 analyst_default_row_limit: int = Field(default=100_000)
 live_db_url: str = Field(default="")

 # ----- helpers -----
 def resolve_provider(self) -> str:
  # explicit override (auto-detection only when provider == "auto")
  if self.llm_provider and self.llm_provider.strip().lower() != "auto":
   p = self.llm_provider.strip().lower()
   if p in {"anthropic", "gemini", "nim", "openrouter"}:
    # Verify the matching key is configured before honoring the override
    if p == "anthropic" and not self.anthropic_api_key.strip():
     return "stub"
    if p == "gemini" and not self.gemini_api_key.strip():
     return "stub"
    if p == "nim" and not (self.openai_api_key or self.openai_compat_api_key or "").strip():
     return "stub"
    if p == "openrouter" and not (self.openai_api_key or self.openai_compat_api_key or "").strip():
     return "stub"
    return p

  if self.anthropic_api_key.strip():
   return "anthropic"
  if self.gemini_api_key.strip():
   return "gemini"
  openai_key = (self.openai_api_key or self.openai_compat_api_key or "").strip()
  if openai_key:
   base = (self.openai_base_url or "").lower()
   if "nvidia" in base or "nim" in base or "integrate.api.nvidia" in base:
    return "nim"
   return "openrouter"
  return "stub"

 def resolve_model(self) -> str:
  if self.llm_model.strip():
   return self.llm_model.strip()
  provider = self.resolve_provider()
  if provider == "nim":
   return (self.openai_model or DEFAULT_MODELS.get("nim", "")).strip()
  return (DEFAULT_MODELS.get(provider) or "").strip()

 def key_for(self, provider: str) -> str:
  p = (provider or "").strip().lower()
  if p in {"nim", "openrouter"}:
   return (self.openai_api_key or self.openai_compat_api_key or "").strip()
  return {
   "anthropic": self.anthropic_api_key,
   "gemini": self.gemini_api_key,
  }.get(p, "").strip()


_settings: Settings | None = None


def get_settings() -> Settings:
 global _settings
 if _settings is None:
  _settings = Settings()
 return _settings
