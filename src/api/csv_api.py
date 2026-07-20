"""CSV upload and run endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.capabilities.tasks import run_csv_agent
from src.db.models import SessionRow
from src.db.session import get_session
from src.services.sessions import create_session, get_session_row, ingest_csvs, schema_summary

router = APIRouter()


@router.post("/sessions")
def create_session_endpoint(session: Session = Depends(get_session)) -> dict:
    row = create_session()
    meta = schema_summary(row.id)
    return ok({
        "id": row.id,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "schema_summary": meta,
    })


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str, session: Session = Depends(get_session)) -> dict:
    row = get_session_row(session_id)
    if row is None:
        raise api_error("not_found", "Session not found", 404)
    meta = schema_summary(session_id)
    return ok({
        "id": row.id,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "schema_summary": meta,
    })


@router.post("/sessions/{session_id}/csv")
async def upload_csv(session_id: str, files: list[UploadFile] = File(...), session: Session = Depends(get_session)) -> dict:
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
