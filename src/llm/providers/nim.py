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
   url = f"{self._base_url}/chat/completions"
   payload = {
    "model": self.model,
    "max_tokens": max_tokens,
    "messages": [
     {"role": "system", "content": system},
     {"role": "user", "content": user},
    ],
   }
   try:
    ret = httpx.post(
     url,
     headers={
      "Authorization": f"Bearer {self._api_key}",
      "content-type": "application/json",
     },
     json=payload,
     timeout=120.0,
    )
   except httpx.LocalProtocolError as e:
    raise RuntimeError(
     f"nim protocol error url={url!r} payload={_safe_payload(payload)!r} error={e!s}"
    ) from e
   except httpx.HTTPError as e:
    raise RuntimeError(f"nim http error url={url!r} error={e!s}") from e

   if ret.status_code != httpx.codes.OK:
    raise RuntimeError(
     f"nim http error status={_status(ret)} url={url!r} body={_body(ret)[:1200]!r}"
    )
   try:
    data = ret.json()
   except Exception as exc:
    raise LLMError(f"nim returned non-JSON response: {_body(ret)[:500]!r}") from exc
   try:
    text = (data["choices"][0]["message"]["content"] or "").strip()
   except (KeyError, IndexError) as exc:
    raise LLMError(f"nim returned no choices: {list(data)}") from exc
   if not text:
    raise LLMError("nim returned an empty completion")
   return text

  return with_retries(_call, provider=self.name)


def _status(response: httpx.Response) -> int:
 return getattr(response, "status_code", -1)


def _body(response: httpx.Response) -> str:
 text = getattr(response, "text", None)
 if callable(text):
  try:
   return text()
  except Exception:
   pass
 return getattr(response, "content", b"") or b""


def _safe_payload(payload: dict) -> dict:
 out = dict(payload)
 msgs = out.get("messages") or []
 if msgs:
  first = dict(msgs[0])
  first["content"] = (first.get("content") or "")[:120] + ("..." if len(first.get("content") or "") > 120 else "")
  out["messages"] = [first] + msgs[1:]
 return out
