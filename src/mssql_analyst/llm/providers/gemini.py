"""Gemini LLM provider — calls into ``google-genai``.

This is the only place that imports a provider SDK. We:
- accept the API key via ``Settings.gemini_api_key`` (``SecretStr`` — only
  unwrapped at the boundary, here, never logged);
- construct a single ``Client`` per process, send system+user once, return
  the parsed JSON body (or raw text);
- never echo the key into logs or errors.

Per ``references/build-runtime-quirks.md`` #1: the new ``google-genai``
SDK rejects the dict-shaped ``contents=[{role:...}]`` with HTTP 400. Use
``GenerateContentConfig(system_instruction=...)`` + a single string
``contents``.
"""

from __future__ import annotations

import json
from typing import Any, Union

from mssql_analyst.config.settings import Settings
from mssql_analyst.llm.providers.base import LLMProvider
from mssql_analyst.llm.types import LLMCallResult
from mssql_analyst.observability.events import get_logger

logger = get_logger("mssql_analyst.llm.gemini")


class GeminiProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._api_key = (
            settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        )
        self._model_name = settings.llm_model or "gemini-3.1-pro"
        self._client: Any = None  # lazy to avoid SDK import-time errors

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai  # type: ignore[import-not-found]
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "google-genai SDK is required for the Gemini provider. "
                    "Install with: uv add google-genai"
                ) from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def complete_json(
        self, *, model: str, system: str, user: str
    ) -> Union[LLMCallResult, dict, str]:
        client = self._get_client()
        try:
            from google.genai import types as genai_types  # type: ignore[import-not-found]

            config = genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            )
        except Exception:  # pragma: no cover — older SDK fallback
            user = f"{system}\n\n{user}"
            try:
                from google.generativeai import types as genai_types  # type: ignore

                config = genai_types.GenerationConfig(response_mime_type="application/json")
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "google-genai SDK is required and is too old; install a recent version."
                ) from exc

        try:
            response = client.models.generate_content(
                model=model or self._model_name,
                contents=user,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"gemini_request_failed: {exc.__class__.__name__}") from exc

        text = getattr(response, "text", None) or _safe_response_text(response)
        if text is None:
            raise RuntimeError("gemini_returned_no_text")
        text = text.strip()

        # Token usage is best-effort — SDK exposes it on ``usage_metadata``.
        in_tok, out_tok = _extract_tokens(response)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = text
        return LLMCallResult(parsed, input_tokens=in_tok, output_tokens=out_tok)


def _safe_response_text(response: Any) -> str | None:
    """Navigate google-genai response shape without exploding on bad payloads."""
    try:
        if hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            chunks = []
            for p in parts:
                if getattr(p, "text", None):
                    chunks.append(p.text)
            return "".join(chunks) if chunks else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _extract_tokens(response: Any) -> tuple[int, int]:
    """Best-effort extraction of (input_tokens, output_tokens)."""
    try:
        meta = getattr(response, "usage_metadata", None) or {}
        # The google-genai SDK spells these differently across versions; cover both.
        for in_attr in ("prompt_token_count", "input_tokens", "promptTokenCount"):
            if hasattr(meta, in_attr):
                in_tok = int(getattr(meta, in_attr) or 0)
                break
        else:
            in_tok = 0
        for out_attr in ("candidates_token_count", "output_tokens", "candidatesTokenCount"):
            if hasattr(meta, out_attr):
                out_tok = int(getattr(meta, out_attr) or 0)
                break
        else:
            out_tok = 0
        # Some SDKs return a dict.
        if isinstance(meta, dict):
            in_tok = int(meta.get("prompt_token_count") or meta.get("input_tokens") or 0)
            out_tok = int(
                meta.get("candidates_token_count") or meta.get("output_tokens") or 0
            )
        return in_tok, out_tok
    except Exception:  # noqa: BLE001
        return 0, 0
