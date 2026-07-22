"""Fraud detection analyst API — read-only queries over live SQL Server."""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.config.settings import get_settings
from src.db.models import AuditRow, RunRow
from src.db.session import get_session
from src.db.live_db import LiveDBQueryError, read_only_query
from src.domain.fraud_detection import FraudDetectionQueryRequest, FraudDetectionQueryResponse
from src.graph.agent_fraud_detection import build_fraud_detection_graph
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.observability.events import get_logger

router = APIRouter()
log = get_logger("fraud_detection_api")


@router.post("/query")
def query_fraud_detection(req: FraudDetectionQueryRequest, session: Session = Depends(get_session)) -> dict:
 if not (req.schema_summary or "").strip():
  raise api_error("bad_request", "schema_summary is required for fraud detection queries.", 400)

 state: AgentState = {
  "question": req.question,
  "schema_summary": (req.schema_summary or "").strip(),
  "row_limit": req.row_limit or 5000,
  "query_plan": None,
  "tables_touched": [],
  "generated_code": None,
  "executed_sql": None,
  "executed_rows": None,
  "executed_columns": None,
  "executed_row_count": None,
  "latency_ms": None,
  "result_table": None,
  "answer_text": None,
  "followups": None,
  "anomaly_flags": None,
  "sensitive_warning": None,
  "provider": None,
  "model": None,
  "token_usage": None,
  "status": None,
  "error": None,
 }

 run = RunRow(input_text=req.question, instruction="", status="running")
 session.add(run)
 session.flush()
 run_id = run.id

 try:
  graph = build_fraud_detection_graph()
  start = time.perf_counter()
  try:
   final = graph.invoke(state)
  except Exception as exc:
   final = {
    "error": str(exc),
    "status": "failed",
    "provider": None,
    "model": None,
    "answer_text": "",
    "executed_sql": None,
    "tables_touched": [],
    "executed_columns": None,
    "executed_rows": None,
    "executed_row_count": None,
    "latency_ms": int((time.perf_counter() - start) * 1000),
    "result_table": None,
    "anomaly_flags": [],
    "sensitive_warning": None,
   }
  latency_ms = final.get("latency_ms") or int((time.perf_counter() - start) * 1000)
  status = final.get("status") or "failed"
  run.status = status
  run.output_text = final.get("answer_text") or ""
  run.provider = final.get("provider")
  run.model = final.get("model")
  run.error_message = final.get("error")
  audit = AuditRow(
   run_id=run_id,
   question=req.question,
   sql=final.get("executed_sql"),
   tables_touched=json.dumps(final.get("tables_touched") or []),
   row_count=final.get("executed_row_count"),
   latency_ms=latency_ms,
   token_usage=json.dumps(final.get("token_usage") or {}),
  )
  session.add(audit)
  session.commit()
 except Exception as exc:
  run.status = "failed"
  run.error_message = str(exc)
  session.commit()
  raise

 columns = final.get("executed_columns") or []
 rows = final.get("executed_rows") or []
 result_table = {"columns": columns, "rows": rows} if columns else None
 response = FraudDetectionQueryResponse(
  run_id=run_id,
  status=run.status,
  generated_sql=final.get("executed_sql"),
  tables_touched=final.get("tables_touched") or [],
  executed_row_count=final.get("executed_row_count"),
  latency_ms=latency_ms,
  provider=run.provider,
  model=run.model,
  error=run.error_message,
  answer_text=run.output_text,
  result_table=result_table,
  served_from_cache=False,
  anomaly_flags=final.get("anomaly_flags") or [],
  sensitive_warning=final.get("sensitive_warning"),
 )
 return ok(response.model_dump())


@router.get("/runs/{run_id}")
def get_fraud_detection_run(run_id: str, session: Session = Depends(get_session)) -> dict:
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"no run with id {run_id}", 404)
 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).first()
 response = FraudDetectionQueryResponse(
  run_id=run.id,
  status=run.status,
  generated_sql=(audit.sql if audit else None),
  tables_touched=(json.loads(audit.tables_touched) if audit and audit.tables_touched else []),
  executed_row_count=(audit.row_count if audit else None),
  latency_ms=(audit.latency_ms if audit else None),
  provider=run.provider,
  model=run.model,
  error=run.error_message,
  answer_text=run.output_text,
 )
 return ok(response.model_dump())


@router.get("/runs/{run_id}/download")
def download_fraud_detection(run_id: str, session: Session = Depends(get_session)) -> dict:
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"no run with id {run_id}", 404)

 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).first()
 result_table = None
 if audit and audit.sql:
  try:
   columns, rows = read_only_query(audit.sql)
   result_table = {"columns": columns, "rows": rows}
  except Exception:
   result_table = None

 return {
  "run_id": run_id,
  "file_name": f"fraud_result_{run_id}.csv",
  "content": run.output_text or "",
  "content_type": "text/csv",
  "result_table": result_table,
  "served_from_cache": False,
 }
