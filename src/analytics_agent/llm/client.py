from typing import Any

import httpx

from analytics_agent.config.settings import Settings, get_settings
from analytics_agent.observability.events import get_logger

logger = get_logger("llm")

SYSTEM_PROMPT = (
    "You are an analytics narrator for a single local business (#local). "
    "Given the acquisition+retention funnel numbers, write one concise, plain-language "
    "insight (2-3 sentences) about what the funnel says and the biggest leak."
)


class LLMClient:
    """OpenRouter-backed client. Falls back to a labelled sample when no key is set."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base_url = "https://openrouter.ai/api/v1"

    @property
    def available(self) -> bool:
        return bool(self.settings.openrouter_api_key)

    def narrate(self, snapshot: Any) -> str | None:
        if not self.available:
            pct = _retention_pct(snapshot)
            return (
                f"[SAMPLE INSIGHT] {snapshot.signup} signups, "
                f"{snapshot.activated} activated, {pct:.0f}% retained. "
                f"Biggest leak is typically signup→activated. "
                f"Set AGENT_OPENROUTER_API_KEY for a live narration."
            )
        try:
            return self._call_openrouter(snapshot)
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the pipeline
            logger.warning("llm.narrate_failed", error=str(exc))
            return f"[insight unavailable: {exc}]"

    def _call_openrouter(self, snapshot: Any) -> str:
        prompt = (
            f"Funnel for #local: visit/install={snapshot.visit_or_install}, "
            f"signup={snapshot.signup}, activated={snapshot.activated}, "
            f"retained={snapshot.retained}, revenue=${snapshot.revenue:,.0f}. "
            "What does this say and where is the biggest leak?"
        )
        body = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 160,
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def _retention_pct(snapshot: Any) -> float:
    if not snapshot.signup:
        return 0.0
    return 100.0 * snapshot.retained / snapshot.signup
