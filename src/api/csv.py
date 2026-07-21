"""CSV analyst API — upload + query over CSV data."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.config.settings import get_settings
from src.db.models import AuditRow, CSVUploadRow, RunRow
from src.db.session import get_session
from src.domain.csv_analyst import CSVQueryRequest, CSVQueryResponse, CSVUploadResponse
from src.graph.runner_csv import run_csv_agent
from src.observability.events import get_logger

router = APIRouter()
log = get_logger("csv_api")


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
 if not file.filename or not file.filename.lower().endswith(".csv"):
  raise api_error("bad_request", "Upload a single .csv file.", 400)

 settings = get_settings()
 workspace_dir = Path(settings.database_url.replace("sqlite:///", "")).parent / "csv_workspace"
 workspace_dir.mkdir(parents=True, exist_ok=True)
 target = workspace_dir / file.filename
 try:
  content = await file.read()
  target.write_bytes(content)
  text = content.decode("utf-8", errors="strict")
  reader = csv.reader(io.StringIO(text))
  header = next(reader)
  row_count = sum(1 for _ in reader)
 except Exception as exc:
  raise api_error("bad_csv", f"Failed to parse {file.filename}: {exc}", 400) from exc

 columns = [c.strip().lower().replace(" ", "_") for c in header]
 fingerprint = json.dumps(sorted(columns))
 row = CSVUploadRow(file_name=file.filename, row_count=row_count, columns=json.dumps(columns), schema_fingerprint=fingerprint)
 session.add(row)
 session.flush()
 session.commit()
 result = CSVUploadResponse(file_id=row.id, file_name=file.filename, row_count=row_count, columns=columns, schema_fingerprint=fingerprint)
 return ok(result.model_dump())


@router.post("/query")
def query_csv(req: CSVQueryRequest, session: Session = Depends(get_session)) -> dict:
 if req.data_source != "csv" or not req.csv_file_ids:
  raise api_error("bad_request", "CSV queries require data_source='csv' and csv_file_ids.", 400)

 run_id = run_csv_agent(session, question=req.question, csv_file_ids=req.csv_file_ids, row_limit=req.row_limit or get_settings().analyst_default_row_limit)
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"run {run_id} vanished", 500)

 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).first()
 response = CSVQueryResponse(
  run_id=run.id,
  status=run.status,
  answer_text=run.output_text,
  generated_sql=(audit.sql if audit else None),
  tables_touched=(json.loads(audit.tables_touched) if audit and audit.tables_touched else None),
  executed_row_count=(audit.row_count if audit else None),
  latency_ms=(audit.latency_ms if audit else None),
  provider=run.provider,
  model=run.model,
  error=run.error_message,
 )
 return ok(response.model_dump())


@router.get("/runs/{run_id}")
def get_csv_run(run_id: str, session: Session = Depends(get_session)) -> dict:
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"no run with id {run_id}", 404)

 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).first()
 response = CSVQueryResponse(
  run_id=run.id,
  status=run.status,
  answer_text=run.output_text,
  generated_sql=(audit.sql if audit else None),
  tables_touched=(json.loads(audit.tables_touched) if audit and audit.tables_touched else None),
  executed_row_count=(audit.row_count if audit else None),
  latency_ms=(audit.latency_ms if audit else None),
  provider=run.provider,
  model=run.model,
  error=run.error_message,
  result_table=None,
 )
 return ok(response.model_dump())


@router.get("/runs/{run_id}/download")
def download_csv(run_id: str, session: Session = Depends(get_session)) -> dict:
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"no run with id {run_id}", 404)

 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).first()
 if not audit or not run.output_text:
  raise api_error("not_ready", "No result available for download yet.", 404)

 return {
  "run_id": run_id,
  "file_name": f"result_{run_id}.csv",
  "content": run.output_text,
  "content_type": "text/csv",
 }
