"""LLM client + provider factory.

Single boundary. Every LLM call in the agent goes through
``LLMClient.call_json(...)`` — no provider SDK is imported elsewhere in the
codebase, which keeps:
- secrets confined to ``Settings.gemini_api_key`` (Pydantic ``SecretStr``);
- provider swap to OpenAI/Anthropic trivial;
- the data-locality test exclusively inspects payloads at this boundary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mssql_analyst.config.settings import get_settings
from mssql_analyst.llm.providers.base import LLMProvider
from mssql_analyst.llm.types import LLMCallResult


@dataclass
class _TemplateRendered:
    """Rendered template broken into system + user shape."""

    system: str
    user: str


class LLMClient:
    """Thin façade over the active ``LLMProvider``.

    The client serialises the user payload to JSON and asks the provider to
    return JSON. Providers also report token usage; we expose it via the
    ``LLMCallResult`` envelope.
    """

    def __init__(self, provider: LLMProvider, *, model: str) -> None:
        self._provider = provider
        self._model = model

    def call_json(
        self,
        *,
        prompt_name: str,
        template: str,
        user_payload: dict[str, Any],
    ) -> LLMCallResult:
        """Call the LLM with a rendered prompt and return parsed JSON + token counts."""
        rendered = _render_template(prompt_name, template, user_payload)
        result = self._provider.complete_json(
            model=self._model,
            system=rendered.system,
            user=rendered.user,
        )
        # Provider contract: returns either ``LLMCallResult`` (preferred) OR
        # a bare parsed JSON (legacy compatibility) — both are acceptable.
        if isinstance(result, LLMCallResult):
            return result
        if isinstance(result, dict) and ("content" in result or "input_tokens" in result):
            # already shaped
            return LLMCallResult(
                result.get("content"),
                input_tokens=result.get("input_tokens", 0) or 0,
                output_tokens=result.get("output_tokens", 0) or 0,
            )
        return LLMCallResult(result)


def _render_template(
    prompt_name: str,
    template: str,
    payload: dict[str, Any],
) -> _TemplateRendered:
    """Render the .md template with the JSON payload baked in.

    Every ``.md`` prompt has a section heading ``## Inputs`` followed by
    ``{{PAYLOAD}}`` which we substitute with the JSON dump.
    """
    body = template
    if "{{PAYLOAD}}" in body:
        body = body.replace("{{PAYLOAD}}", json.dumps(payload, default=_json_default, indent=2))
    for key, val in payload.items():
        body = body.replace("{{" + key + "}}", json.dumps(val, default=_json_default))
    return _TemplateRendered(
        system=f"# {prompt_name}\n\n{body}",
        user=json.dumps(payload, default=_json_default),
    )


def _json_default(obj: Any) -> Any:
    """JSON fallback — handles datetime etc."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:  # noqa: BLE001
            return repr(obj)
    return repr(obj)


# ---------------------------------------------------------------------------
# module-resolution cache
# ---------------------------------------------------------------------------

_default_client: LLMClient | None = None


def get_default_llm_client() -> LLMClient:
    """Module-level cached client. Tests can monkeypatch the providers."""
    global _default_client
    if _default_client is None:
        from mssql_analyst.llm.providers.factory import create_provider

        settings = get_settings()
        provider = create_provider(settings)
        _default_client = LLMClient(provider, model=settings.llm_model)
    return _default_client


def reset_default_llm_client() -> None:
    """Test-only — drop the cached client so the next call rebuilds."""
    global _default_client
    _default_client = None
