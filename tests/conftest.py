"""Pytest fixtures — settings singleton reset + DB isolation."""

from __future__ import annotations

import os
import pytest

# Ensure the app config picks up a dummy key if missing — tests use a
# RecordingProvider / stub; the real provider is hit only in the
# integration tests that opt in via the `live` marker.
os.environ.setdefault("APP_GEMINI_API_KEY", "test-key-does-not-call-real-provider")


@pytest.fixture(autouse=True)
def _reset_settings():
    """Drop cached Settings so env patches in each test take effect."""
    from cctns_analyst.config import settings as settings_module
    from cctns_analyst.llm import client as llm_client_module

    settings_module._reset_settings()
    llm_client_module.reset_default_llm_client()
    yield
    settings_module._reset_settings()
    llm_client_module.reset_default_llm_client()


@pytest.fixture
def temp_sqlite_db(tmp_path, monkeypatch):
    """Redirect the app DB to a tmp SQLite file for the test."""
    from cctns_analyst.config import settings as settings_module
    from cctns_analyst.db import session as session_module
    from cctns_analyst.db.models import Base

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{db_path}")
    settings_module._reset_settings()

    # Reset cached engine and rebuild.
    session_module.reset_engine()
    engine = session_module.get_engine()
    Base.metadata.create_all(engine)
    yield str(db_path)
    session_module.reset_engine()
