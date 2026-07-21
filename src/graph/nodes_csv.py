"""Graph nodes — CSV analyst path.

Each node reads from and writes to ``AgentState``. Failures go into ``state["error"]``
so the conditional edges route to ``handle_error``. LLM calls are batched: one call
per node that needs the model.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from src.config.settings import get_settings
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError


def _workspace_sqlite_path() -> Path:
 settings = get_settings()
 raw = settings.database_url.replace("sqlite:///", "")
 base = Path(raw)
 return base.parent / "csv_workspace" / "working.db"


def plan_query(state: AgentState) -> AgentState:
 try:
  client = LLMClient()
  system = load_prompt("csv_analyst_plan")
  schema = state.get("schema_summary") or "{}"
  user = (
   f"QUESTION: {state['instruction']}\n\n"
   f"SCHEMA (table_name -> [columns]):\n{schema}\n\n"
   "Plan: which tables and columns to use. Return ONLY a compact JSON like:\n"
   '{"tables": ["upload_1"], "columns": ["col1", "col2"], "notes": "..."}'
  )
  raw = client.complete(system, user, max_tokens=512).strip()
  plan = json.loads(raw) if raw.startswith("{") else {"tables": [], "columns": [], "notes": raw}
  state["query_plan"] = raw
  state["tables_touched"] = plan.get("tables") or []
  state["provider"] = client.provider_name
  state["model"] = client.model
 except LLMError as exc:
  return {"error": f"plan_query failed: {exc}"}
 return state


def generate_code(state: AgentState) -> AgentState:
 try:
  client = LLMClient()
  system = load_prompt("csv_analyst_sql")
  tables = state.get("tables_touched") or []
  schema = state.get("schema_summary") or "{}"
  user = (
   f"QUESTION: {state['instruction']}\n\n"
   f"SCHEMA (table_name -> [columns]):\n{schema}\n\n"
   f"USE_TABLES: {', '.join(tables)}\n\n"
   "Emit ONE read-only SELECT SQL query for SQLite. Return ONLY the SQL, no markdown fences."
  )
  sql = client.complete(system, user, max_tokens=1024).strip()
  # Strip accidental markdown fences if the model adds them.
  if sql.startswith("```"):
   sql = sql.split("\n", 1)[-1]
  if sql.endswith("```"):
   sql = sql.rsplit("\n", 1)[0]
  state["generated_code"] = sql
  state["executed_sql"] = sql
  state["provider"] = client.provider_name
  state["model"] = client.model
 except LLMError as exc:
  return {"error": f"generate_code failed: {exc}"}
 return state


def execute_query(state: AgentState) -> AgentState:
 sql = state.get("executed_sql") or ""
 if not sql.strip():
  return {"error": "execute_query: no SQL to execute."}
 tables = state.get("tables_touched") or []
 db_path = _workspace_sqlite_path()
 if not db_path.exists():
  return {"error": f"execute_query: workspace DB missing at {db_path}"}

 t0 = time.perf_counter()
 try:
  conn = sqlite3.connect(db_path)
  conn.row_factory = sqlite3.Row
  try:
   cur = conn.execute(sql)
   rows = cur.fetchall()
   columns = list(rows[0].keys()) if rows else []
   data = [dict(r) for r in rows]
  finally:
   conn.close()
  latency_ms = int((time.perf_counter() - t0) * 1000)
  state["executed_rows"] = data
  state["executed_columns"] = columns
  state["executed_row_count"] = len(data)
  state["latency_ms"] = latency_ms
 except Exception as exc:
  return {"error": f"execute_query failed: {exc}"}
 return state


def assemble_answer(state: AgentState) -> AgentState:
 try:
  client = LLMClient()
  system = load_prompt("csv_analyst_answer")
  rows = state.get("executed_rows") or []
  columns = state.get("executed_columns") or []
  sample = rows[:10]
  user = (
   f"QUESTION: {state['instruction']}\n\n"
   f"SQL: {state.get('executed_sql') or ''}\n\n"
   f"COLUMNS: {columns}\n\n"
   f"ROW_COUNT: {len(rows)}\n\n"
   f"SAMPLE_ROWS (JSON):\n{json.dumps(sample, default=str, indent=2)}\n\n"
   "Return ONLY a JSON object:\n"
   '{"answer": "...", "followups": ["..."], "anomalies": ["..."], "sensitive_warning": null}'
  )
  raw = client.complete(system, user, max_tokens=1024).strip()
  parsed = json.loads(raw) if raw.startswith("{") else {"answer": raw, "followups": [], "anomalies": []}
  state["answer_text"] = parsed.get("answer")
  state["followups"] = parsed.get("followups") or []
  state["anomaly_flags"] = parsed.get("anomalies") or []
  state["sensitive_warning"] = parsed.get("sensitive_warning")
  state["provider"] = client.provider_name
  state["model"] = client.model
  state["result_table"] = {"columns": columns, "rows": rows}
 except LLMError as exc:
  return {"error": f"assemble_answer failed: {exc}"}
 return state


def finalize(state: AgentState) -> AgentState:
 return {"status": "completed"}


def handle_error(state: AgentState) -> AgentState:
 return {"status": "failed"}
