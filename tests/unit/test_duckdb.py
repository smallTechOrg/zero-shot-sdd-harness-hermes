"""CSV/DuckDB cache tests (unit)."""
from __future__ import annotations

import pytest

from src.db.duckdb_store import get_schema, init_session, ingest_csv, query


@pytest.fixture()
def session_id():
    sid = "testsession"
    init_session(sid)
    yield sid


def test_ingest_and_schema(session_id):
    csv = b"name,value\nfoo,1\nbar,2\n"
    info = ingest_csv(session_id, "t1", csv)
    assert info["name"] == "t1"
    assert info["row_count"] == 2
    assert len(info["columns"]) == 2

    schema = get_schema(session_id)
    assert schema[0]["name"] == "t1"
    assert schema[0]["row_count"] == 2
    assert schema[0]["columns"][0]["name"] == "name"
