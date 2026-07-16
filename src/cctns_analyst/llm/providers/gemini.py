"""Gemini LLM provider — calls into ``google-genai``.

This is the only place that imports a provider SDK.  We:
- accept the api key via ``Settings.gemini_api_key`` (``SecretStr`` — only
  unwrapped at the boundary, here, never logged);
- construct a single ``Client`` per request, send system+user once, return
  the parsed JSON body or free text;
- never echo the key into logs or errors.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from cctns_analyst.config.settings import Settings
from cctns_analyst.llm.providers.base import LLMProvider

logger = logging.getLogger("cctns_analyst.llm.gemini")


class GeminiProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        self._model_name = settings.llm_model or "gemini-2.5-flash"
        # ``google-genai`` accepts the key via env; we set it inside ``complete_json``
        # so the value never sits in ``os.environ`` longer than one call.
        self._client = None  # lazily built on first call to avoid SDK import-time errors

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai  # type: ignore[import-not-found]
            except Exception as exc:  # noqa: BLE001 — surface as a clear error
                raise RuntimeError(
                    "google-genai SDK is required for the Gemini provider. "
                    "Install with: uv add google-genai"
                ) from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def complete_json(self, *, model: str, system: str, user: str) -> Any:
        client = self._get_client()
        # In newer google-genai, use ``GenerateContentConfig(system_instruction=...)``
        # and a single user ``contents=`` entry. The dict-shape ``contents``
        # with role=system is rejected as 400.
        try:
            from google.genai import types as genai_types  # type: ignore[import-not-found]

            config = genai_types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            )
        except Exception:  # pragma: no cover - older SDK fallback
            from google.generativeai import types as genai_types  # type: ignore[import-not-found]
            config = genai_types.GenerationConfig(response_mime_type="application/json")
            # system instruction is concatenated into user text as a fallback
            user = f"{system}\n\n{user}"

        try:
            response = client.models.generate_content(
                model=model or self._model_name,
                contents=user,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 — propagate via graph state, not raise
            raise RuntimeError(f"gemini_request_failed: {exc.__class__.__name__}") from exc
        text = getattr(response, "text", None) or _safe_response_text(response)
        if text is None:
            raise RuntimeError("gemini_returned_no_text")
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


def _safe_response_text(response: Any) -> str | None:
    """Navigate google-genai response shape without exploding on bad payloads."""
    try:
        # New SDK shape
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
