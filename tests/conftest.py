"""Pytest fixtures — settings singleton reset + DB isolation."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_settings():
    """Drop cached Settings so env patches in each test take effect."""
    from mssql_analyst.config import settings as settings_module
    from mssql_analyst.llm import client as llm_client_module

    settings_module._reset_settings()
    llm_client_module.reset_default_llm_client()
    yield
    settings_module._reset_settings()
    llm_client_module.reset_default_llm_client()


@pytest.fixture
def temp_sqlite_db(tmp_path, monkeypatch):
    """Redirect the audit-log DB to a tmp SQLite file for the test."""
    from mssql_analyst.config import settings as settings_module
    from mssql_analyst.db import session as session_module
    from mssql_analyst.db.models import Base

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("AGENT_DATABASE_URL", f"sqlite:///{db_path}")
    settings_module._reset_settings()
    session_module.reset_engine()
    engine = session_module.get_engine()
    Base.metadata.create_all(engine)
    yield str(db_path)
    session_module.reset_engine()
