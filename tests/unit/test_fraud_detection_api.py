"""Unit tests for the fraud detection API."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


@pytest.fixture()
def client():
 with TestClient(create_app()) as c:
  yield c


def test_fraud_query_rejects_empty_schema(client):
 res = client.post("/fraud-detection/query", json={"question": "suspicious repeats", "schema_summary": ""})
 assert res.status_code == 400


def test_fraud_query_missing_run_is_404(client):
 res = client.get("/fraud-detection/runs/nope")
 assert res.status_code == 404
