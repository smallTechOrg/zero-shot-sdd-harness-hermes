"""Ingest routes — POST /api/v1/ingest"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api._common import api_error, ok
from src.db.duckdb_store import get_schema, init_session, ingest_csv

router = APIRouter()


class IngestResponse(BaseModel):
    session_id: str
    session_name: str | None = None
    tables: list[dict[str, Any]]
    status: str


@router.post("/ingest")
async def ingest(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise api_error("invalid_request", "Upload at least one CSV file.", 422)
    session_id = "sess1"  # Phase1: simple shared session; refine later.
    init_session(session_id)
    tables: list[dict[str, Any]] = []
    for upload in files:
        data = await upload.read()
        name = (upload.filename or "upload.csv").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        table_name = name.rsplit(".", 1)[0]
        table_name = "".join(c if c.isalnum() or c == "_" else "_" for c in table_name) or "t"
        info = ingest_csv(session_id, table_name, data)
        tables.append(info)
    schema = get_schema(session_id)
    schema_md = _schema_to_text(schema)
    return ok(
        {
            "session_id": session_id,
            "session_name": "Imported CSVs",
            "tables": tables,
            "schema_markdown": schema_md,
            "status": "ok",
        }
    )


@router.get("/schema")
def schema(session_id: str) -> dict:
    tables = get_schema(session_id)
    return ok({"tables": tables, "markdown": _schema_to_text(tables)})


def _schema_to_text(tables: list[dict[str, Any]]) -> str:
    lines = []
    for t in tables:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        lines.append(f"{t['name']} — {t['row_count']} rows: {cols}")
    return "\n".join(lines) or "(no tables)"


@router.get("/sessions")
def get_sessions() -> dict:
    return ok({"sessions": [{"session_id": "sess1", "name": "Imported CSVs", "tables_count": 1}]})
