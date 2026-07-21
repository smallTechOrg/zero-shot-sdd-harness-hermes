"""Unit tests for the runs API — history + audit trace."""
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
