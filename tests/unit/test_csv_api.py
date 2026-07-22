"""Unit tests for the CSV analyst API endpoints."""
from __future__ import annotations

import csv
import io

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


@pytest.fixture()
def client():
 with TestClient(create_app()) as c:
  yield c


def test_upload_csv_returns_file_id_and_schema(client):
 payload = b"district,offence,count\nLucknow,Theft,10\nKanpur,Theft,7\n"
 files = {"file": ("test.csv", io.BytesIO(payload), "text/csv")}
 res = client.post("/csv/upload", files=files)
 assert res.status_code == 200
 body = res.json()["data"]
 assert body["file_name"] == "test.csv"
 assert body["row_count"] == 2
 assert set(body["columns"]) == {"district", "offence", "count"}
 assert isinstance(body["file_id"], int)


def test_upload_rejects_non_csv(client):
 payload = b"hello world"
 files = {"file": ("notes.txt", io.BytesIO(payload), "text/plain")}
 res = client.post("/csv/upload", files=files)
 assert res.status_code == 400


def test_query_csv_returns_run_id(client):
 upload_payload = b"district,offence,count\nLucknow,Theft,10\nKanpur,Theft,7\n"
 upload_res = client.post("/csv/upload", files={"file": ("q.csv", io.BytesIO(upload_payload), "text/csv")})
 assert upload_res.status_code == 200
 upload = upload_res.json()["data"]
 file_id = upload["file_id"]

 res = client.post("/csv/query", json={"question": "Which district has the highest count?", "data_source": "csv", "csv_file_ids": [file_id]})
 assert res.status_code == 200
 body = res.json()["data"]
 assert "run_id" in body
 assert body["status"] in {"completed", "failed"}
