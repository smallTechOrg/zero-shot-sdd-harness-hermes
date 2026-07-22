"""Unit tests for the runs API — history + audit trace + source dispatch."""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


@pytest.fixture()
def client():
 with TestClient(create_app()) as c:
  yield c


def test_list_runs_returns_empty_when_no_runs(client):
 res = client.get("/runs")
 assert res.status_code == 200
 body = res.json()["data"]
 assert body == []


def test_get_run_history_404_for_missing_run(client):
 res = client.get("/runs/does-not-exist")
 assert res.status_code == 404


def test_run_audit_trace_404_for_missing_run(client):
 res = client.get("/runs/does-not-exist/audit")
 assert res.status_code == 404
 body = res.json()["detail"]
 assert isinstance(body, dict)
 assert body.get("code") == "run_not_found"


def test_create_run_defaults_to_transform(client):
 res = client.post("/runs", json={"text": "hello", "instruction": "upper"})
 assert res.status_code == 200
 body = res.json()["data"]
 assert body["status"] in {"completed", "failed"}
 assert "run_id" in body


def test_create_run_preserves_data_source_field(client):
 res = client.post(
 "/runs",
 json={
  "text": "hello",
  "instruction": "upper",
  "data_source": "transform",
 },
 )
 assert res.status_code == 200
 body = res.json()["data"]
 assert body["status"] in {"completed", "failed"}
 assert "run_id" in body


def test_create_run_rejects_invalid_data_source_value(client):
 res = client.post("/runs", json={"text": "hello", "data_source": "whatever"})
 assert res.status_code == 422
