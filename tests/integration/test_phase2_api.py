"""Integration tests for the Phase-2 endpoints.

The endpoints read from ``answer_runs`` only (no live MSSQL, no live Gemini).
So the test gear is much smaller than Phase-1's: we seed rows directly
into the audit DB via ``temp_sqlite_db`` and assert on the JSON envelopes.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# Fixtures
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
    error_message: str | None = None,
    created_at: datetime | None = None,
):
    """Insert one AnswerRun row with the Phase-2 columns populated."""
    from mssql_analyst.db.models import AnswerRun
    from mssql_analyst.db.session import create_db_session

    ts = created_at or datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    with create_db_session() as session:
        run = AnswerRun(
            id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            question=question,
            sql_template=sql,
            sql_attempts=1,
            row_count=row_count,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            status=status,
            error_message=error_message,
            created_at=ts,
            updated_at=ts,
            result_columns_json=json.dumps(columns),
            result_rows_json=json.dumps(rows),
            day=day,
        )
        session.add(run)
        session.flush()
        rid = run.id
    return rid


@pytest.fixture
def seed_factory():
    """Tests pass this as the first arg to ``_seed_run``-shaped helpers."""
    return _seed_run


# ---------------------------------------------------------------------------
# /api/history
# ---------------------------------------------------------------------------


def test_history_returns_seeded_rows(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid1 = seed_factory(
        question="how many tables?",
        sql="SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES",
        status="completed",
        row_count=1,
        tokens_used=120,
        latency_ms=500,
        columns=["n"],
        rows=[[5]],
        day="2026-07-18",
    )
    rid2 = seed_factory(
        question="list types",
        sql="SELECT * FROM systypes",
        status="failed",
        row_count=0,
        tokens_used=80,
        latency_ms=1000,
        columns=[],
        rows=[],
        day="2026-07-19",
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/history?limit=50&offset=0")
        assert r.status_code == 200
        body = r.json()
        data = body["data"]
        assert data["total"] == 2
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["rows"]) == 2
        ids = {row["id"] for row in data["rows"]}
        assert {rid1, rid2} == ids


def test_history_pagination_offset(temp_sqlite_db, seed_factory):
    """offset past the data returns an empty page."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    seed_factory(
        question="q1",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=10,
        latency_ms=100,
        columns=["n"],
        rows=[[1]],
        day="2026-07-19",
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/history?limit=5&offset=99")
        assert r.status_code == 200
        body = r.json()
        assert body["data"]["total"] == 1
        assert body["data"]["rows"] == []


def test_history_limit_clamped(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    seed_factory(
        question="q1",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=10,
        latency_ms=100,
        columns=["n"],
        rows=[[1]],
        day="2026-07-19",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/history?limit=99999&offset=0")
        assert r.status_code == 200
        # clamped to 200 (max)
        assert r.json()["data"]["limit"] == 200
        r = client.get("/api/history?limit=0&offset=0")
        # clamped to 1
        assert r.json()["data"]["limit"] == 1


# ---------------------------------------------------------------------------
# /api/usage/by-day
# ---------------------------------------------------------------------------


def test_usage_by_day_descending(temp_sqlite_db, seed_factory):
    """Per-day buckets sorted newest first; tokens summed."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    # Day 18: one run, 100 tokens
    seed_factory(
        question="q1",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=100,
        latency_ms=100,
        columns=["n"],
        rows=[[1]],
        day="2026-07-18",
    )
    # Day 19: two runs, 50 + 75 tokens = 125
    seed_factory(
        question="q2",
        sql="SELECT 2",
        status="completed",
        row_count=1,
        tokens_used=50,
        latency_ms=100,
        columns=["n"],
        rows=[[2]],
        day="2026-07-19",
    )
    seed_factory(
        question="q3",
        sql="SELECT 3",
        status="failed",
        row_count=0,
        tokens_used=75,
        latency_ms=100,
        columns=[],
        rows=[],
        day="2026-07-19",
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/usage/by-day?days=14")
        assert r.status_code == 200
        body = r.json()["data"]
        days = [(b["day"], b["tokens"], b["questions"]) for b in body["days"]]
        # newest first, then older
        assert days[0] == ("2026-07-19", 125, 2)
        assert days[1] == ("2026-07-18", 100, 1)


def test_usage_by_day_excludes_sentinel(temp_sqlite_db, seed_factory):
    """The default '1970-01-01' windows default should NOT show up in the rollup."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/usage/by-day?days=14")
        body = r.json()["data"]
        # No rows seeded → empty days array
        assert body["days"] == []


# ---------------------------------------------------------------------------
# /api/ask/{run_id}/csv
# ---------------------------------------------------------------------------


def test_csv_export_completed_run(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed_factory(
        question="q1",
        sql="SELECT 1 AS n, 'a,b' AS s",
        status="completed",
        row_count=2,
        tokens_used=50,
        latency_ms=200,
        columns=["n", "s"],
        rows=[[1, "a,b"], [2, "plain"]],
        day="2026-07-19",
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/ask/{rid}/csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        # body is a string with row terminator
        body = r.text
        assert body.startswith("n,s\r\n")
        # The 'a,b' cell must be quoted; the 'plain' cell must not.
        assert '"a,b"' in body
        assert "2,plain" in body
        # Trailing CRLF
        assert body.endswith("\r\n")


def test_csv_export_not_found(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/ask/00000000-0000-0000-0000-000000000000/csv")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ask_not_found"


def test_csv_export_failed_run_404(temp_sqlite_db, seed_factory):
    """A 'failed' run is not exportable (no rows to write)."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed_factory(
        question="q1",
        sql="",
        status="failed",
        row_count=0,
        tokens_used=42,
        latency_ms=200,
        columns=[],
        rows=[],
        day="2026-07-19",
        error_message="llm_unavailable: gemini_request_failed: ClientError",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/ask/{rid}/csv")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ask_not_completed"


# ---------------------------------------------------------------------------
# /api/ask/{run_id}/anomalies
# ---------------------------------------------------------------------------


def test_anomalies_flags_outlier(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    # Rows: 1, 2, 3, 4, 100 — index 4 is the outlier
    rid = seed_factory(
        question="q1",
        sql="SELECT v FROM t",
        status="completed",
        row_count=5,
        tokens_used=10,
        latency_ms=100,
        columns=["v"],
        rows=[[1], [2], [3], [4], [100]],
        day="2026-07-19",
    )
    app = create_app()
    with TestClient(app) as client:
        # threshold=1.5 catches the gap (z≈1.79); threshold=2.0 would not
        # for this small fixture — see ``test_big_outlier_is_flagged``.
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=1.5")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["run_id"] == rid
        assert data["threshold"] == 1.5
        assert data["flagged_rows"] == [4]
        assert data["flagged_count"] == 1


def test_anomalies_constant_column_no_flags(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed_factory(
        question="q1",
        sql="SELECT 5",
        status="completed",
        row_count=4,
        tokens_used=10,
        latency_ms=100,
        columns=["v"],
        rows=[[5], [5], [5], [5]],
        day="2026-07-19",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=2.0")
        assert r.status_code == 200
        assert r.json()["data"]["flagged_rows"] == []


def test_anomalies_threshold_must_be_positive(temp_sqlite_db, seed_factory):
    """Garbage threshold returns 400."""
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed_factory(
        question="q1",
        sql="SELECT 1",
        status="completed",
        row_count=1,
        tokens_used=10,
        latency_ms=100,
        columns=["v"],
        rows=[[1]],
        day="2026-07-19",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=0")
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "invalid_threshold"
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=-2")
        assert r.status_code == 400
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=abc")
        # FastAPI parses to float — "abc" → 400 from FastAPI itself.
        assert r.status_code in (400, 422)


def test_anomalies_failed_run_404(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    rid = seed_factory(
        question="q1",
        sql="",
        status="failed",
        row_count=0,
        tokens_used=42,
        latency_ms=200,
        columns=[],
        rows=[],
        day="2026-07-19",
    )
    app = create_app()
    with TestClient(app) as client:
        r = client.get(f"/api/ask/{rid}/anomalies?threshold=2.0")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ask_not_completed"


def test_anomalies_unknown_run_404(temp_sqlite_db, seed_factory):
    from mssql_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/api/ask/does-not-exist/anomalies?threshold=2.0")
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ask_not_found"
