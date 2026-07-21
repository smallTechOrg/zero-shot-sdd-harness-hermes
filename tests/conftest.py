"""Shared fixtures.

Every test gets: reset settings/db singletons + an isolated tmp SQLite DB.
Unit tests additionally blank the provider keys; integration tests keep the
real key from .env (that is the point of the gate).
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_singletons():
 """Reset cached settings + engine so env patches take effect per test."""
 import src.config.settings as settings_mod
 import src.db.session as session_mod

 settings_mod._settings = None
 session_mod._engine = None
 session_mod._SessionLocal = None
 yield
 settings_mod._settings = None
 if session_mod._engine is not None:
  session_mod._engine.dispose()
  session_mod._engine = None
  session_mod._SessionLocal = None


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
 """Point the app at a fresh SQLite file — never the user's real DB."""
 monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
 yield


@pytest.fixture()
def no_keys(monkeypatch):
 """Simulate 'no provider key configured' regardless of the user's .env.

 Env vars override .env values in pydantic-settings, so empty strings are
 enough — the file itself is never touched.
 """
 monkeypatch.setenv("AGENT_LLM_PROVIDER", "auto")
 monkeypatch.setenv("AGENT_LLM_MODEL", "")
 monkeypatch.setenv("AGENT_ANTHROPIC_API_KEY", "")
 monkeypatch.setenv("AGENT_GEMINI_API_KEY", "")
 monkeypatch.setenv("OPENAI_API_KEY", "")
 monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "")
 yield
