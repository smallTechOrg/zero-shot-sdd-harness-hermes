"""Configuration loaded from the repo-root .env (never committed).

Secrets are read from the environment only. The raw key value is never logged,
echoed, or returned in any response — we only ever assert *presence*.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (the app is run from the repo root). Repeat-load is a
# no-op if already loaded; safe.
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")


class Config:
    # Gemini
    GEMINI_API_KEY: str = os.environ.get("AGENT_GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("AGENT_GEMINI_MODEL", "models/gemini-2.5-flash")

    # Server
    HOST: str = os.environ.get("AUTO_PODCASTER_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("AUTO_PODCASTER_PORT", "8001"))

    # Storage
    DATA_DIR: Path = _REPO_ROOT / "data"
    DB_PATH: Path = DATA_DIR / "podcasts.db"

    # Dialogue limits
    MAX_TURNS: int = int(os.environ.get("AUTO_PODCASTER_MAX_TURNS", "12"))

    @property
    def gemini_key_present(self) -> bool:
        return bool(self.GEMINI_API_KEY)


config = Config()
