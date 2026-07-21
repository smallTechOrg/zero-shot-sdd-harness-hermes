"""DB routes — stub/live connection management."""
from __future__ import annotations

from fastapi import APIRouter

from src.api._common import api_error, ok
from src.db.mssql_connector import (
    live_query,
    live_schema,
    test_connection,
)

router = APIRouter()


@router.get("/db/test-connection")
def test_db() -> dict:
    try:
        info = test_connection()
    except Exception as exc:
        raise api_error("db_unavailable", str(exc), 503) from exc
    return ok(info)


@router.get("/db/schema")
def db_schema() -> dict:
    try:
        tables = live_schema()
    except Exception as exc:
        raise api_error("db_unavailable", str(exc), 503) from exc
    return ok({"tables": tables})
