"""LLM client + provider factory.

Single boundary.  Every LLM call in the agent goes through
``LLMClient.complete_json(...)`` — no provider SDK is imported elsewhere in
the codebase, which keeps:
- secrets confined to ``Settings.gemini_api_key`` (Pydantic ``SecretStr``);
- provider swap to OpenAI/Anthropic trivial;
- the data-locality test exclusively inspects ``complete_json`` payloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from cctns_analyst.config.settings import get_settings
from cctns_analyst.llm.providers.base import LLMProvider


@dataclass
class _TemplateRendered:
    """Rendered template broken into a system + user shape."""

    system: str
    user: str


class LLMClient:
    """Thin façade over the active ``LLMProvider``.

    The client serialises the user payload to JSON and asks the provider to
    return JSON. Providers may also expose a synchronous ``complete`` for
    free-form text — not used here.
    """

    def __init__(self, provider: LLMProvider, *, model: str) -> None:
        self._provider = provider
        self._model = model

    def complete_json(
        self,
        *,
        prompt_name: str,
        template: str,
        user_payload: dict[str, Any],
    ) -> Any:
        """Call the LLM with a rendered prompt and parse JSON from the reply.

        ``prompt_name`` is used for log observability only (request_id comes
        via the caller).  Returns either a dict (the parsed JSON) or the
        raw text string when the provider did not return structured JSON —
        callers handle both forms, with bias toward "treat as dict".
        """
        rendered = _render_template(prompt_name, template, user_payload)
        # The prompt-spy test intercepts this method and inspects the
        # rendered dict before it is sent — so we make sure that what is
        # sent over the wire is exactly this object.
        raw = self._provider.complete_json(
            model=self._model,
            system=rendered.system,
            user=rendered.user,
        )
        return raw


def _render_template(
    prompt_name: str,
    template: str,
    payload: dict[str, Any],
) -> _TemplateRendered:
    """Render the .md template with the JSON payload baked in.

    The convention is simple: every ``.md`` prompt has a section heading
    ``## Inputs`` followed by a fenced block that names the keys in JSON.
    We substitute a single ``{{PAYLOAD}}`` placeholder with the JSON dump.
    Prompts may also include literal ``{{question}}`` etc. as a convenience
    and we substitute those too.
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
    """JSON fallback — handles numpy/datetime as best-effort."""
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
        from cctns_analyst.llm.providers.factory import create_provider

        settings = get_settings()
        provider = create_provider(settings)
        _default_client = LLMClient(provider, model=settings.llm_model)
    return _default_client


def reset_default_llm_client() -> None:
    """Test-only — drop the cached client so the next call rebuilds."""
    global _default_client
    _default_client = None


# Used in unit tests to verify the boundary
class _RecordingProvider(Protocol):
    def complete_json(self, *, model: str, system: str, user: str) -> Any: ...
