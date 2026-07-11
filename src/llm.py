"""Gemini teaching-text client — ONE call per drill set.

The LLM produces teaching text (explanation + hint framing + tip) and is
asked to *propose* a note, but the backend **ignores** the proposed name
and computes its own. Token usage is captured and returned.

If the key is missing or the call fails, a deterministic fallback string is
returned with used_fallback=True so exercises still work.
"""

from __future__ import annotations

import os
import json
import logging

logger = logging.getLogger("music_tutor.llm")

SYSTEM_PROMPT = (
    "You are a patient music-theory tutor for adults who never learned to "
    "read staff notation. Explain the given topic in at most 3 short "
    "sentences, friendly and concrete. Include one memorable tip. Do NOT "
    "present any note name as a graded answer — you are teaching, not quizzing."
)

_FALLBACK = (
    "Read notes by their position on the staff. The treble clef's bottom line "
    "is E; the bass clef's is G. Count line-space-line upward. Tip: learn the "
    "notes on the lines and spaces as little phrases (Every Good Boy Deserves "
    "Fun / FACE)."
)


def _load_key() -> str:
    # Load from .env manually; presence-only — never print the value.
    key = os.environ.get("AGENT_GEMINI_API_KEY", "")
    if not key:
        try:
            with open(".env") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AGENT_GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            pass
    return key


def generate_teaching(topic: str, clef: str) -> dict:
    """Return {text, tokens:{prompt,completion,total}, model, used_fallback}."""
    key = _load_key()
    model = os.environ.get("AGENT_LLM_MODEL") or "gemini-2.5-flash"
    if not key:
        logger.warning("AGENT_GEMINI_API_KEY not set — using fallback teaching text")
        return {
            "text": _FALLBACK,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "model": model,
            "used_fallback": True,
        }
    try:
        from google import genai

        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=model,
            contents=f"Topic: {topic} on the {clef} clef. Briefly teach it.",
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.7,
                "max_output_tokens": 200,
            },
        )
        text = (resp.text or "").strip()
        usage = getattr(resp, "usage_metadata", None)
        tokens = {
            "prompt": getattr(usage, "prompt_token_count", 0) or 0,
            "completion": getattr(usage, "candidates_token_count", 0) or 0,
            "total": getattr(usage, "total_token_count", 0) or 0,
        }
        return {
            "text": text or _FALLBACK,
            "tokens": tokens,
            "model": model,
            "used_fallback": False,
        }
    except Exception as exc:  # pragma: no cover - network/key failure path
        logger.warning("Gemini call failed (%s) — using fallback teaching text", exc)
        return {
            "text": _FALLBACK,
            "tokens": {"prompt": 0, "completion": 0, "total": 0},
            "model": model,
            "used_fallback": True,
        }
