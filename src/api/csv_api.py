"""CSV upload and run endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.capabilities.tasks import run_csv_agent
from src.db.models import SessionRow
from src.db.session import get_session
from src.services.sessions import create_session, get_session_row, ingest_csvs, schema_summary

router = APIRouter()


@router.post("/sessions")
def create_session_endpoint() -> dict:
    # Create a session using the service function which returns a SessionRow.
    data = create_session()
    # Get the schema summary (should be empty for a new session)
    meta = schema_summary(data.id)
    return ok({
        "id": data.id,
        "status": data.status,
        "created_at": data.created_at,
        "schema_summary": meta,
    })


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str) -> dict:
    row = get_session_row(session_id)
    if row is None:
        raise api_error("not_found", "Session not found", 404)
    meta = schema_summary(session_id)
    return ok({
        "id": row.id,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "schema_summary": meta,
    })


@router.post("/sessions/{session_id}/csv")
async def upload_csv(session_id: str, files: List[UploadFile] = File(...)) -> dict:
    row = get_session_row(session_id)
    if row is None:
        raise api_error("not_found", "Session not found", 404)
    uploads: list[tuple[str, bytes]] = []
    errors: list[str] = []
    for upload in files:
        try:
            uploads.append((upload.filename, await upload.read()))
        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")
    summary, ingest_errors = ingest_csvs(session_id, uploads)
    errors.extend(ingest_errors)
    return ok({
        "session_id": session_id,
        "tables": summary["tables"],
        "errors": errors,
        "count": len(summary["tables"]),
    })