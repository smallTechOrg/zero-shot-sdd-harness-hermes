"""run_live_db_query() — live database analyst path."""
from __future__ import annotations

import json
import time

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.db.models import AuditRow, RunRow
from src.graph.runner_csv import build_csv_graph
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.db.live_db import read_only_query


def run_live_db_query(session: Session, *, question: str, schema_summary: str, row_limit: int = 5000) -> str:
 state = {
  "run_id": None,
  "input_text": question,
  "instruction": "",
  "data_source": "live_db",
  "csv_file_ids": [],
  "schema_summary": schema_summary.strip(),
  "query_plan": None,
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
  "tables_touched": None,
  "provider": None,
  "model": None,
  "token_usage": None,
  "memory_context": None,
  "saved_workspace_id": None,
  "status": None,
  "error": None,
 }

 client = LLMClient()
 plan_system = load_prompt("live_db_analyst_plan")
 plan_user = (
  f"QUESTION: {question}\n\n"
  f"SCHEMA (table -> JSON description):\n{schema_summary}\n\n"
  "Return ONLY compact JSON with shape: "
  '{"tables": [...], "columns": [...], "join_conditions": "...", "rationale": "..."}\n'
 )
 raw = client.complete(plan_system, plan_user, max_tokens=512).strip()
 plan = {}
 try:
  plan = json.loads(raw)
 except Exception:
  pass

 sql_system = load_prompt("live_db_analyst_sql")
 sql_user = (
  f"QUESTION: {question}\n\n"
  f"SCHEMA (table -> JSON description):\n{schema_summary}\n\n"
  f"TABLES: {', '.join(plan.get('tables') or [])}\n"
  f"COLUMNS: {', '.join(plan.get('columns') or [])}\n\n"
  "Emit ONE read-only SELECT SQL for SQL Server. Return ONLY the SQL, no markdown fences."
 )
 sql = client.complete(sql_system, sql_user, max_tokens=1024).strip()
 if sql.startswith("```"):
  sql = sql.split("\n", 1)[-1]
 if sql.endswith("```"):
  sql = sql.rsplit("\n", 1)[0]
 state["executed_sql"] = sql
 state["tables_touched"] = plan.get("tables") or []

 t0 = time.perf_counter()
 try:
  columns, rows = read_only_query(sql)
  latency_ms = int((time.perf_counter() - t0) * 1000)
  state["executed_columns"] = columns
  state["executed_rows"] = rows[: min(row_limit, 5000)]
  state["executed_row_count"] = len(rows)
  state["latency_ms"] = latency_ms
 except Exception as exc:
  state["error"] = f"live_db query failed: {exc}"
  state["status"] = "failed"

 run = RunRow(input_text=question, instruction="", status=run.status, output_text=run.output_text, provider=run.provider, model=run.model, error_message=run.error_message)
 session.add(run)
 session.flush()
 run_id = run.id

 audit = AuditRow(run_id=run_id, question=question, sql=sql, tables_touched=json.dumps(state["tables_touched"]), row_count=state["executed_row_count"], latency_ms=state["latency_ms"], token_usage="{}")
 session.add(audit)
 session.commit()
 return run_id


def run_live_db_queryv2(session: Session, *, question: str, schema_summary: str, row_limit: int = 5000) -> str:
 state = {
  "run_id": None,
  "question": question,
  "schema_summary": schema_summary,
  "data_source": "live_db",
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
  "memory_context": None,
  "saved_workspace_id": None,
  "status": None,
  "error": None,
 }

 client = LLMClient()
 plan_system = load_prompt("live_db_analyst_plan")
 plan_user = (
  f"QUESTION: {question}\n\n"
  f"SCHEMA (table -> JSON description):\n{schema_summary}\n\n"
  "Return ONLY compact JSON with shape: "
  '{"tables": [...], "columns": [...], "join_conditions": "...", "rationale": "..."}\n'
 )
 plan_raw = client.complete(plan_system, plan_user, max_tokens=512).strip()
 plan = {}
 try:
  plan = json.loads(plan_raw)
 except Exception:
  pass

 sql_system = load_prompt("live_db_analyst_sql")
 sql_user = (
  f"QUESTION: {question}\n\n"
  f"SCHEMA (table -> JSON description):\n{schema_summary}\n\n"
  f"TABLES: {', '.join(plan.get('tables') or [])}\n"
  f"COLUMNS: {', '.join(plan.get('columns') or [])}\n\n"
  "Emit ONE read-only SELECT SQL for SQL Server. Return ONLY the SQL, no markdown fences."
 )
 sql = client.complete(sql_system, sql_user, max_tokens=1024).strip()
 if sql.startswith("```"):
  sql = sql.split("\n", 1)[-1]
 if sql.endswith("```"):
  sql = sql.rsplit("\n", 1)[0]
 state["executed_sql"] = sql
 state["tables_touched"] = plan.get("tables") or []

 t0 = time.perf_counter()
 try:
  columns, rows = read_only_query(sql, row_limit=row_limit)
  latency_ms = int((time.perf_counter() - t0) * 1000)
  state["executed_columns"] = columns
  state["executed_rows"] = rows
  state["executed_row_count"] = len(rows)
  state["latency_ms"] = latency_ms
  state["result_table"] = {"columns": columns, "rows": rows}
 except Exception as exc:
  state["error"] = str(exc)
  state["status"] = "failed"

 answer_prompt = load_prompt("live_db_analyst_answer")
 answer_user = (
  f"QUESTION: {question}\n\n"
  f"SQL: {sql}\n\n"
  f"COLUMNS: {state['executed_columns']}\n\n"
  f"ROW_COUNT: {state['executed_row_count']}\n\n"
  f"SAMPLE_ROWS (JSON):\n{json.dumps((state['executed_rows'] or [])[:10], default=str, indent=2)}\n\n"
  "Return ONLY JSON: {\"answer\": \"...\", \"followups\": [...], \"anomalies\": [...], \"sensitive_warning\": null}\n"
 )
 answer_raw = client.complete(answer_prompt, answer_user, max_tokens=1024).strip()
 try:
  answer_obj = json.loads(answer_raw)
  state["answer_text"] = answer_obj.get("answer") or answer_raw
 except Exception:
  state["answer_text"] = answer_raw

 run = RunRow(input_text=question, instruction="", status=state.get("status", "completed"), output_text=state.get("answer_text") or "", provider=client.provider_name, model=client.model, error_message=state.get("error"))
 session.add(run)
 session.flush()
 run_id = run.id
 audit = AuditRow(run_id=run_id, question=question, sql=sql, tables_touched=json.dumps(state.get("tables_touched") or []), row_count=state.get("executed_row_count"), latency_ms=state.get("latency_ms"), token_usage="{}")
 session.add(audit)
 session.commit()
 return run_id
