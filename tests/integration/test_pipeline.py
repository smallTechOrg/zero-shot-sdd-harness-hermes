"""Integration gate — runs against the REAL LLM/API with keys from .env.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import create_app
from src.config.settings import get_settings
from src.db.models import RunRow
from src.db.session import create_db_session


def _require_key() -> None:
    if get_settings().resolve_provider() == "stub":
        pytest.skip("no real LLM key in .env — integration gate requires one")


@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c


def test_happy_path_real_llm_end_to_end(client):
    _require_key()
    # 1. Create a session
    res = client.post("/sessions")
    assert res.status_code == 200
    session_id = res.json()["data"]["id"]

    # 2. Upload a CSV file
    csv_content = b"value\n1\n2\n3"
    res = client.post(
        f"/sessions/{session_id}/csv",
        files=[("files", ("data.csv", csv_content, "text/csv"))],
    )
    assert res.status_code == 200
    assert res.json()["data"]["count"] == 1

    # 3. Run the agent with a question
    res = client.post(
        "/runs",
        json={"session_id": session_id, "question": "What is the sum of the value column?"},
    )
    assert res.status_code == 200
    run = res.json()["data"]
    assert run["status"] == "completed", f"run failed: {run['error_message']}"
    assert run["output_text"] is not None
    # Check that the output contains the sum (6)
    assert "6" in run["output_text"]

    # 4. Check DB state
    with create_db_session() as s:
        row = s.get(RunRow, run["run_id"])
        assert row is not None
        assert row.status == "completed"
        assert row.output_text == run["output_text"]
        assert row.provider == get_settings().resolve_provider()


def test_edge_case_short_input_real_llm(client):
    _require_key()
    # 1. Create a session
    res = client.post("/sessions")
    assert res.status_code == 200
    session_id = res.json()["data"]["id"]

    # 2. Upload a CSV file
    csv_content = b"value\n10"
    res = client.post(
        f"/sessions/{session_id}/csv",
        files=[("files", ("data.csv", csv_content, "text/csv"))],
    )
    assert res.status_code == 200

    # 3. Run the agent with a question
    res = client.post(
        "/runs",
        json={"session_id": session_id, "question": "What is the value?"},
    )
    assert res.status_code == 200
    run = res.json()["data"]
    assert run["status"] == "completed", f"run failed: {run['error_message']}"
    assert run["output_text"] is not None
    # Check that the output contains the value (10)
    assert "10" in run["output_text"]