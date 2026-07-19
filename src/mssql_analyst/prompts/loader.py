"""Prompt loader — reads .md templates from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=16)
def load_prompt(name: str) -> str:
    """Return the raw .md contents for ``name``. Cached."""
    p = _PROMPTS_DIR / f"{name}.md"
    if not p.exists():
        raise FileNotFoundError(f"prompt template not found: {p}")
    return p.read_text(encoding="utf-8")


def clear_cache() -> None:
    """Test-only — drop the loader cache."""
    load_prompt.cache_clear()
