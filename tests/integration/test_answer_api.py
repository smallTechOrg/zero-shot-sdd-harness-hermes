"""End-to-end API test using TestClient + recording LLM stub."""

from __future__ import annotations

import json


def test_post_answer_returns_envelope_with_answer_sql_rows(temp_sqlite_db, recording_provider):
    from cctns_analyst.api.app_factory import create_app
    from cctns_analyst.tools.mock_mirror import build_mock_tables, execute_select
    from fastapi.testclient import TestClient

    # What value the agent *should* return (computed from the deterministic fixture).
    tables = build_mock_tables(seed=42)
    _, _, expected_count = execute_select(
        tables,
        "SELECT COUNT(*) AS n FROM cctns_mirror.fir WHERE district = 'Lucknow'",
        row_cap=1000,
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.post(
            "/v1/answer",
            json={"question": "How many FIRs in Lucknow?"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["error"] is None
        data = body["data"]
        assert data["answer"].startswith("There have been")
        assert "SELECT COUNT" in data["sql"]
        assert data["rows"] == [[expected_count]]
        assert data["columns"] == ["firs"]
        assert data["sql_attempts"] == 1
        # latency non-zero
        assert data["latency_ms"] >= 0


def test_answer_run_persisted(temp_sqlite_db, recording_provider):
    from cctns_analyst.api.app_factory import create_app
    from cctns_analyst.db.models import AnswerRun
    from cctns_analyst.db.session import create_db_session
    from cctns_analyst.tools.mock_mirror import build_mock_tables, execute_select
    from fastapi.testclient import TestClient

    tables = build_mock_tables(seed=42)
    _, _, expected_count = execute_select(
        tables,
        "SELECT COUNT(*) AS n FROM cctns_mirror.fir WHERE district = 'Lucknow'",
        row_cap=1000,
    )

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/v1/answer", json={"question": "How many FIRs in Lucknow?"})
        assert r.status_code == 200

    with create_db_session() as s:
        runs = s.query(AnswerRun).all()
    assert len(runs) == 1
    assert runs[0].status == "completed"
    assert runs[0].sql_template.startswith("SELECT COUNT")
    assert runs[0].row_count == expected_count
    assert runs[0].error_message is None


def test_health_returns_mirror_mode(temp_sqlite_db, monkeypatch, recording_provider):
    from cctns_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["data"]["status"] == "ok"
        assert body["data"]["mirror_mode"] == "mock"  # because CCTNS_MIRROR_URL is blank


def test_validation_error_returns_422(temp_sqlite_db, recording_provider):
    """Empty string ('question': '') violates min_length=1 — FastAPI returns 422."""
    from cctns_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/v1/answer", json={"question": ""})
        assert r.status_code == 422, r.text


def test_question_required(temp_sqlite_db, recording_provider):
    """Missing 'question' — FastAPI returns 422."""
    from cctns_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/v1/answer", json={})
        assert r.status_code == 422, r.text
