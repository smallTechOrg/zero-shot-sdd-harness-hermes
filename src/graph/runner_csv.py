"""run_csv_agent() — CSV analyst path.

Creates the run row, builds the one-shot analyst graph, invokes it, and
persists the outcome + audit row.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import AuditRow, CSVUploadRow, RunRow
from src.graph.agent_csv import build_csv_graph
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt


def _workspace_sqlite_path() -> Path:
 settings = get_settings()
 raw = settings.database_url.replace("sqlite:///", "")
 base = Path(raw)
 return base.parent / "csv_workspace" / "working.db"


def run_csv_agent(session: Session, *, question: str, csv_file_ids: list[int], row_limit: int) -> str:
 log_prefix = "run_csv_agent"

 run = RunRow(input_text=question, instruction="", status="running")
 session.add(run)
 session.flush()
 run_id = run.id

 try:
  uploads = session.query(CSVUploadRow).filter(CSVUploadRow.id.in_(csv_file_ids)).all()
  if not uploads:
   raise ValueError("No CSV uploads found for the provided ids.")

  workspace_db = _workspace_sqlite_path()
  workspace_db.parent.mkdir(parents=True, exist_ok=True)

  # Register CSVs into the workspace SQLite DB.
  import sqlite3

  conn = sqlite3.connect(workspace_db)
  try:
   for upload in uploads:
    csv_path = workspace_db.parent / upload.file_name
    if not csv_path.exists():
     raise ValueError(f"Missing uploaded file: {upload.file_name}")
    df = __import__("pandas").read_csv(csv_path)
    df.to_sql(f"upload_{upload.id}", conn, if_exists="replace", index=False)
  finally:
   conn.close()

  state: AgentState = {
   "run_id": run_id,
   "input_text": "",
   "instruction": question,
   "data_source": "csv",
   "csv_file_ids": list(csv_file_ids),
   "schema_summary": json.dumps({str(u.id): json.loads(u.columns or "[]") for u in uploads}),
   "query_plan": None,
   "generated_code": None,
   "executed_sql": None,
   "executed_rows": None,
   "executed_columns": None,
   "executed_row_count": None,
   "latency_ms": None,
   "result_table": None,
   "answer_text": None,
   "csv_download_url": None,
   "followups": None,
   "anomaly_flags": None,
   "sensitive_warning": None,
   "tables_touched": None,
   "provider": None,
   "model": None,
   "token_usage": None,
   "memory_context": None,
   "saved_workspace_id": None,
   "status": None,
   "error": None,
  }

  graph = build_csv_graph()
  start = time.perf_counter()
  final = graph.invoke(state)
  latency_ms = int((time.perf_counter() - start) * 1000)

  run.status = final.get("status", "completed") or "completed"
  run.output_text = final.get("answer_text") or ""
  run.provider = final.get("provider")
  run.model = final.get("model")
  run.error_message = final.get("error")

  audit = AuditRow(
   run_id=run_id,
   question=question,
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

 return run_id
