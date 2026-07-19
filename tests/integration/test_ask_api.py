"""tests/integration/test_ask_api.py — integration tests.

Two swaps happen BEFORE any graph invocation:

1. ``stub_connector`` — the process-wide ``MssqlConnector`` singleton is
   replaced by an in-memory fake. We do this by monkey-patching both the
   module-level ``_connector`` slot AND resetting the cached instance via
   ``reset_mssql_connector()`` so the next ``get_mssql_connector()`` call
   rebuilds with the same class — except we also override the class via
   ``monkeypatch.setattr(mssql_mod, 'MssqlConnector', FakeConnector)`` so
   ``MssqlConnector()`` inside ``reset_mssql_connector() -> re-import path``
   returns the fake.  This belt-and-braces lets us pin both the class and
   the instance.
2. ``stub_llm`` — replaces the factory so the ``LLMClient`` wraps a stub
   provider that scripted responses.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Stub connector
# ---------------------------------------------------------------------------


def _make_fake_connector():
    """Build a single FakeConnector instance (Python doesn't allow instance
    attributes in fixture generator scope)."""

    class FakeConnector:
        def __init__(self) -> None:
            self._schema_cache = {
                "INFORMATION_SCHEMA.TABLES": [
                    {"name": "TABLE_NAME", "type": "varchar"},
                    {"name": "TABLE_TYPE", "type": "varchar"},
                ]
            }
            self.last_sql: str | None = None

        def describe_schema(self):
            return self._schema_cache

        def execute(self, sql):
            self.last_sql = sql
            if "RUNTIME_SHOULD_FAIL" in sql:
                class _Exc(Exception):
                    pass
                raise _Exc("simulated_mssql_failure")
            return ["answer_n"], [(41,)], 1

    return FakeConnector()


@pytest.fixture
def stub_connector(monkeypatch):
    """Replace the live MSSQL connector with a fake for the lifetime of one test.

    The graph imports ``MssqlConnector`` from ``tools.mssql`` lazily (inside
    ``run_agent``), so patching that module's class symbol is sufficient.
    We also need to swap the connector class inside ``nodes.build_nodes``,
    which captures it at call time, so we also patch the symbol it does see.
    """
    import mssql_analyst.tools.mssql as mssql_mod
    from mssql_analyst.graph import nodes as nodes_mod

    fake = _make_fake_connector()
    FakeConnector = type(fake)

    monkeypatch.setattr(mssql_mod, "MssqlConnector", FakeConnector)
    monkeypatch.setattr(nodes_mod, "connector_singleton", fake)
    # Force the connector to come back via the FakeConnector class on next call.
    mssql_mod.reset_mssql_connector()
    return fake


# ---------------------------------------------------------------------------
# Stub LLM provider
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_llm(monkeypatch):
    """Replace ``create_provider`` with a stub that records every call."""
    from mssql_analyst import llm
    from mssql_analyst.llm.providers import base
    from mssql_analyst.llm.types import LLMCallResult

    calls: list[dict] = []

    class StubProvider(base.LLMProvider):
        def __init__(self) -> None:
            self._responses = [
                LLMCallResult(
                    {"sql": "SELECT 41 AS answer_n FROM INFORMATION_SCHEMA.TABLES"}
                ),
            ]
            self._idx = 0

        def complete_json(self, *, model, system, user):
            calls.append({"model": model, "system": system, "user": user})
            payload = self._responses[self._idx]
            self._idx += 1
            return payload

    stub = StubProvider()

    def fake(settings):
        return stub

    monkeypatch.setattr(
        "mssql_analyst.llm.providers.factory.create_provider",
        fake,
    )
    llm.client.reset_default_llm_client()
    return {"stub": stub, "calls": calls}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_ask_returns_envelope(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/ask",
            json={"question": "How many tables are in master?"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["error"] is None
        data = body["data"]
        assert data["sql"].startswith("SELECT")
        assert data["rows"] == [[41]]
        assert data["columns"] == ["answer_n"]
        assert data["row_count"] == 1
        assert data["sql_attempts"] == 1
        assert data["status"] == "completed"


def test_answer_run_persisted(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from mssql_analyst.db.models import AnswerRun
    from mssql_analyst.db.session import create_db_session
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/ask",
            json={"question": "How many tables are in master?"},
        )
        assert r.status_code == 200

    with create_db_session() as s:
        runs = s.query(AnswerRun).all()
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].sql_template.startswith("SELECT")


def test_usage_returns_totals(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        # First ask so an AnswerRun row exists.
        r = client.post(
            "/api/ask",
            json={"question": "How many tables are in master?"},
        )
        assert r.status_code == 200
        r2 = client.get("/api/usage")
        assert r2.status_code == 200
        body = r2.json()
        data = body["data"]
        assert data["total_questions"] >= 1
        assert isinstance(data["last_questions"], list)


def test_health_smoke(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "ok"
        assert body["mssql_mode"] in {"live", "unconfigured"}


def test_empty_question_400(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/ask", json={"question": ""})
        # Whitespace-only is rejected at the API; the empty-body 422 is from
        # Pydantic `min_length=1`.
        assert r.status_code in {422, 400}


def test_missing_question_422(temp_sqlite_db, stub_connector, stub_llm):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/ask", json={})
        assert r.status_code == 422


def test_unsafe_sql_rejected_by_validator(temp_sqlite_db, stub_connector, stub_llm):
    """If the LLM emits DROP, the validator must reject with `unsafe_sql`, NOT
    hit the connector. The stub LLM produces safe SQL here — this test
    asserts the validator's behaviour directly via ``assert_select_only``.
    """
    from mssql_analyst.tools.validator import UnsafeSQLError, assert_select_only

    with pytest.raises(UnsafeSQLError):
        assert_select_only("DROP TABLE x")


def test_data_locality_prompt_has_no_rows(temp_sqlite_db, stub_connector, stub_llm):
    """The nl_to_sql payload should embed *schema only*, never raw rows."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/api/ask",
            json={"question": "How many tables are in master?"},
        )
        assert r.status_code == 200

    # The stub recorded the rendered payloads.
    calls = stub_llm["calls"]
    assert len(calls) == 1
    body = calls[0]["user"]
    # Schema must be present.
    assert "INFORMATION_SCHEMA.TABLES" in body
    # Question must be present.
    assert "How many tables are in master?" in body
    # No row arrays.
    assert '"rows"' not in body
