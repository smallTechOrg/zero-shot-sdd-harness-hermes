"""REST routes — extended for CSV upload + NL query."""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.config.settings import get_settings
from src.db.session import create_db_session
from src.db.models import RunRow
from src.graph.runner import run_agent
from src.llm.tools.sql_execute import sql_execute, datasource_info
from src.observability.events import get_logger

router = APIRouter()
log = get_logger("api")

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- request/response models ----------
class QueryRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1)
    datasource_id: str | None = None


class QueryResponse(BaseModel):
    run_id: str
    answer: str | None = None
    code_display: str | None = None
    sql_result: dict[str, Any] | None = None
    evaluate_score: float | None = None
    iteration_count: int | None = None
    latency_ms: int | None = None
    cache_hit: bool = False
    status: str = "pending"
    error_message: str | None = None


class UploadResponse(BaseModel):
    session_id: str
    datasets: list[dict[str, Any]]


class DatasourceConnectRequest(BaseModel):
    session_id: str | None = None
    name: str
    host: str
    database: str
    username: str
    password: str
    port: int = 1433


# ---------- helpers ----------
def _new_session_id() -> str:
    return str(uuid.uuid4())


# ---------- routes ----------
@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_csvs(files: list[UploadFile] = File(...), session_id: str | None = None):
    """Upload one or more CSV files and register them as a session's datasets."""
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    sid = session_id or _new_session_id()
    datasets: list[dict[str, Any]] = []

    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=422, detail=f"Unsupported file: {upload.filename}")

        dest = UPLOAD_DIR / f"{sid}_{upload.filename}"
        content = await upload.read()
        if len(content) > 200 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large: {upload.filename}")

        dest.write_bytes(content)

        try:
            import pandas as pd
            from sqlalchemy import create_engine

            df = pd.read_csv(dest, low_memory=False)
            table_name = f"upload_{sid}_{Path(upload.filename).stem}"
            table_name = re.sub(r"[^a-zA-Z0-9_]", "_", table_name)[:63]

            db_url = get_settings().database_url
            engine = create_engine(db_url)
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            engine.dispose()

            schema = {
                "columns": list(df.columns),
                "row_count": int(len(df)),
                "sample_rows": df.head(5).where(pd.notnull(df), None).values.tolist(),
            }
        except Exception as exc:  # noqa: BLE001
            log.error("upload.ingest_failed", filename=upload.filename, error=str(exc))
            raise HTTPException(status_code=422, detail=f"Failed to ingest {upload.filename}: {exc}")

        datasets.append(
            {
                "id": str(uuid.uuid4()),
                "name": upload.filename,
                "source_type": "csv",
                "schema": schema,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return UploadResponse(session_id=sid, datasets=datasets)


@router.post("/datasource/connect")
def connect_mssql(req: DatasourceConnectRequest):
    """Phase 2 endpoint: connect to MsSQL. In Phase 1, returns 503 with a clear message."""
    raise HTTPException(status_code=503, detail="MsSQL connectivity is a Phase 2 feature")


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """Ask a natural-language question against the active datasource."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    start = perf_counter()
    try:
        initial: dict[str, Any] = {
            "run_id": str(uuid.uuid4()),
            "user_id": "anonymous",
            "question": req.question,
            "datasource_id": req.datasource_id,
            "uploaded_files": [],
            "iteration": 0,
            "max_iterations": 3,
            "error": None,
            "checkpoint": None,
            "plan": None,
            "sql": None,
            "sql_result": None,
            "evaluate_score": None,
            "answer": None,
            "code_display": None,
            "chart_urls": None,
            "download_urls": None,
        }

        final = run_query(initial)
        run_id = final.get("run_id", initial["run_id"])
        latency_ms = int((perf_counter() - start) * 1000)
        sql = final.get("code_display") or final.get("sql") or ""
        sql_result = final.get("sql_result") or {}

        with create_db_session() as s:
            row = RunRow(
                id=run_id,
                question=req.question,
                datasource_id=req.datasource_id,
                generated_sql=sql,
                result_row_count=sql_result.get("row_count"),
                latency_ms=latency_ms,
                status="failed" if final.get("error") else "completed",
                error_message=final.get("error"),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            s.add(row)
            s.flush()

        return QueryResponse(
            run_id=run_id,
            answer=final.get("answer"),
            code_display=sql,
            sql_result=sql_result,
            evaluate_score=final.get("evaluate_score"),
            iteration_count=final.get("iteration"),
            latency_ms=latency_ms,
            cache_hit=False,
            status="failed" if final.get("error") else "completed",
            error_message=final.get("error"),
        )
    except Exception as exc:  # noqa: BLE001
        log.error("query.failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
