"""Unit tests for the live DB API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


@pytest.fixture()
def client():
 with TestClient(create_app()) as c:
  yield c


def test_live_db_query_rejects_empty_question(client):
 res = client.post("/live-db/query", json={"question": "", "schema_summary": "t1(c1)"})
 assert res.status_code == 422


def test_live_db_query_rejects_missing_schema(client):
 res = client.post("/live-db/query", json={"question": "count rows"})
 assert res.status_code == 400


def test_live_db_query_missing_schema_returns_400(client):
 res = client.post("/live-db/query", json={"question": "Count total rows."})
 assert res.status_code == 400


def test_live_db_query_validates_http_error_shape(client):
 payload = {
  "question": "Count rows",
  "schema_summary": "crime(offence text, district text, year int)",
 }
 res = client.post("/live-db/query", json=payload)
 assert res.status_code in {200, 400, 422, 502}
 body = res.json()
 assert "data" in body or "detail" in body


def test_live_db_run_detail_404_for_missing_run(client):
 res = client.get("/live-db/runs/nope")
 assert res.status_code == 404
