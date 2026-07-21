"""NVIDIA NIM provider — OpenAI-compatible chat/completions over httpx.

This adapter covers NVIDIA NIM endpoints as well as any other OpenAI-compatible
service that exposes a `/chat/completions` endpoint.
"""
from __future__ import annotations

import httpx

from src.llm.providers.base import LLMError, LLMProvider
from src.llm.retry import with_retries


class NIMProvider(LLMProvider):
 name = "nim"

 def __init__(self, api_key: str, model: str, base_url: str = "https://integrate.api.nvidia.com/v1") -> None:
  self._api_key = api_key
  self.model = model
  self._base_url = base_url.rstrip("/")

 def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
  def _call() -> str:
   resp = httpx.post(
    f"{self._base_url}/chat/completions",
    headers={
     "Authorization": f"Bearer {self._api_key}",
     "content-type": "application/json",
    },
    json={
     "model": self.model,
     "max_tokens": max_tokens,
     "messages": [
      {"role": "system", "content": system},
      {"role": "user", "content": user},
     ],
    },
    timeout=120.0,
   )
   resp.raise_for_status()
   data = resp.json()
   try:
    text = (data["choices"][0]["message"]["content"] or "").strip()
   except (KeyError, IndexError) as exc:
    raise LLMError(f"nim returned no choices: {list(data)}") from exc
   if not text:
    raise LLMError("nim returned an empty completion")
   return text

  return with_retries(_call, provider=self.name)
