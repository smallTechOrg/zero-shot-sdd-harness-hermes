"""Integration gate — runs against the REAL LLM/API with keys from .env.

Skips when no key is present. Asserts response content and DB
state, not just status codes; covers happy path + edge case + error path.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from io import BytesIO

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


def _post_csv(client: TestClient, instruction: str, rows: str):
    return client.post(
        "/runs",
        data={"instruction": instruction},
        files={"files": ("dataset.csv", BytesIO(rows.encode("utf-8")), "text/csv")},
    )


def test_happy_path_real_llm_end_to_end(client):
    _require_key()
    csv = "station,district,fir_count\nA,Noida,12\nB,Ghaziabad,9\n"
    res = _post_csv(client, "List district totals in one sentence.", csv)
    assert res.status_code == 200
    run = res.json()["data"]
    assert run["status"] == "completed", f"run failed: {run['error_message']}"
    assert run["output_text"]
    body = run["output_text"].lower()
    assert "noida" in body and "ghaziabad" in body

    with create_db_session() as s:
        row = s.get(RunRow, run["run_id"])
        assert row is not None
        assert row.status == "completed"
        assert row.output_text == run["output_text"]


def test_edge_case_single_row_real_llm(client):
    _require_key()
    csv = "x,y\n1,2\n"
    res = _post_csv(client, "Report x and y.", csv)
    assert res.status_code == 200
    run = res.json()["data"]
    assert run["status"] == "completed", f"run failed: {run['error_message']}"
    assert "1" in run["output_text"] and "2" in run["output_text"]


def test_error_path_bad_model_fails_actionably(client, monkeypatch):
    _require_key()
    monkeypatch.setenv("AGENT_LLM_MODEL", "this-model-does-not-exist-xyz")
    import src.config.settings as settings_mod

    settings_mod._settings = None
    csv = "a,b\n1,2\n"
    res = _post_csv(client, "What is a+b?", csv)
    assert res.status_code == 200
    run = res.json()["data"]
    assert run["status"] == "failed"
    assert run["error_message"]
