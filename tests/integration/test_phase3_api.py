"""Phase-3 tests.

Two suites:

- ``test_phase3_retry.py`` — graph retry on validator rejection (unit +
  integration via a stub LLM).
- ``test_phase3_token_aware.py`` — ``shrink_row_cap`` path inside the
  runner is wired through (tokens_used grows → row cap shrinks).
- ``test_timeline_api.py`` — ``GET /api/runs/{run_id}/timeline`` happy +
  404 + the timeline includes validator attempts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_run(
    *,
    question: str,
    sql: str,
    status: str,
    row_count: int,
    tokens_used: int,
    latency_ms: int,
    columns: list[str],
    rows: list[list],
    day: str = "2026-07-19",
    sql_attempts: int = 1,
    timeline: list[dict] | None = None,
    timeline_json: str | None = None,
    error_message: str | None = None,
):
    from mssql_analyst.db.models import AnswerRun
    from mssql_analyst.db.session import create_db_session

    with create_db_session() as session:
        run = AnswerRun(
            id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            question=question,
            sql_template=sql,
            sql_attempts=sql_attempts,
            row_count=row_count,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            status=status,
            error_message=error_message,
            created_at=datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc),
            result_columns_json=json.dumps(columns),
            result_rows_json=json.dumps(rows),
            day=day,
            timeline_json=timeline_json if timeline_json is not None
            else json.dumps(timeline or []),
        )
        session.add(run)
        session.flush()
        rid = run.id
    return rid


@pytest.fixture
def seed():
    """Tests pass this as the first arg to ``_seed_run``."""
    return _seed_run


# ---------------------------------------------------------------------------
# /api/runs/{run_id}/timeline
# ---------------------------------------------------------------------------


def test_timeline_endpoint_unknown_run_404(temp_sqlite_db, seed):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/runs/00000000-0000-0000-0000-000000000000/timeline")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ask_not_found"


def test_timeline_endpoint_happy_path(temp_sqlite_db, seed):
    """A completed run surfaces its persisted timeline."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    timeline = [
        {"node": "nl_to_sql", "started_ms": 100, "duration_ms": 412, "attempts": 1},
        {"node": "validate_sql", "started_ms": 512, "duration_ms": 4, "clean": True,
         "complaints": 0},
        {"node": "execute_sql", "started_ms": 516, "duration_ms": 2401,
         "row_count": 1, "row_cap_effective": 1000, "tokens_at_exec": 0},
    ]
    rid = seed(
        question="q",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=200,
        latency_ms=2817,
        columns=["n"],
        rows=[[1]],
        timeline=timeline,
        sql_attempts=1,
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/runs/{rid}/timeline")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["run_id"] == rid
        assert body["status"] == "completed"
        assert body["tokens_used"] == 200
        assert body["sql_attempts"] == 1
        assert body["node_count"] == 3
        assert body["timeline"][0]["node"] == "nl_to_sql"
        assert body["timeline"][2]["node"] == "execute_sql"


def test_timeline_endpoint_corrupt_json_recovers(temp_sqlite_db, seed):
    """A row whose timeline_json is invalid JSON returns ``timeline=[]``."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed(
        question="q",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=10,
        latency_ms=100,
        columns=["n"],
        rows=[[1]],
        timeline_json="not-json",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/runs/{rid}/timeline")
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["timeline"] == []
        assert body["node_count"] == 0
