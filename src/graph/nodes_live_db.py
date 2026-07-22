"""Graph nodes — live database analyst path.

Each node reads from and writes to ``AgentState``. Failures go into ``state["error"]``
so the conditional edge routes to ``handle_failure``.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from src.config.settings import get_settings
from src.db.live_db import LiveDBQueryError, read_only_query as _read_only_query
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError


def plan_query(state: AgentState) -> AgentState:
 try:
  client = LLMClient()
  system = load_prompt("live_db_analyst_plan")
  user = (
   f"QUESTION: {state['question']}\n\n"
   f"SCHEMA:\n{state['schema_summary']}\n\n"
   "Plan: which tables, columns, join keys, and a short rationale."
   " Return ONLY compact JSON with shape: "
   '{"tables": [...], "columns": [...], "join_conditions": "...", "rationale": "..."}\n'
  )
  raw = client.complete(system, user, max_tokens=512).strip()
  plan: dict = {}
  if raw.startswith("{"):
   try:
    plan = json.loads(raw)
   except Exception:
    plan = {"notes": raw}
  else:
   plan = {"notes": raw}
  state["query_plan"] = plan
  state["tables_touched"] = plan.get("tables") or []
  state["provider"] = client.provider_name
  state["model"] = client.model
 except LLMError as exc:
  return {"error": f"plan_query failed: {exc}"}
 return state


def generate_code(state: AgentState) -> AgentState:
 try:
  plan = state.get("query_plan") or {}
  client = LLMClient()
  system = load_prompt("live_db_analyst_sql")
  user = (
   f"QUESTION: {state['question']}\n\n"
   f"SCHEMA:\n{state['schema_summary']}\n\n"
   f"TABLES: {', '.join(plan.get('tables') or [])}\n"
   f"COLUMNS: {', '.join(plan.get('columns') or [])}\n\n"
   "Emit ONE read-only SELECT SQL for SQL Server. Return ONLY the SQL, no markdown fences."
  )
  sql = client.complete(system, user, max_tokens=1024).strip()
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
  return {"error": "execute_query: no SQL provided."}
 t0 = time.perf_counter()
 try:
  wait_for_live_db_ok()
  columns, rows = _read_only_query(sql)
  latency_ms = int((time.perf_counter() - t0) * 1000)
  state["executed_columns"] = columns
  state["executed_rows"] = rows[: state.get("row_limit") or 5000]
  state["executed_row_count"] = len(rows)
  state["latency_ms"] = latency_ms
  state["result_table"] = {"columns": columns, "rows": rows[: state.get("row_limit") or 5000]}
 except Exception as exc:
  return {"error": f"execute_query failed: {exc}"}
 return state


def assemble_answer(state: AgentState) -> AgentState:
 try:
  client = LLMClient()
  system = load_prompt("live_db_analyst_answer")
  rows = state.get("executed_rows") or []
  columns = state.get("executed_columns") or []
  user = (
   f"QUESTION: {state['question']}\n\n"
   f"SQL: {state.get('executed_sql') or ''}\n\n"
   f"COLUMNS: {columns}\n\n"
   f"ROW_COUNT: {len(state.get('executed_rows') or [])}\n\n"
   f"SAMPLE_ROWS:\n{json.dumps(rows[:10], default=str, indent=2)}\n\n"
   "Return ONLY JSON: {\"answer\": \"...\", \"followups\": [...], \"anomalies\": [...], \"sensitive_warning\": null}"
  )
  raw = client.complete(system, user, max_tokens=1024).strip()
  parsed = {}
  try:
   parsed = json.loads(raw)
  except Exception:
   parsed = {"answer": raw}
  state["answer_text"] = parsed.get("answer") or raw
  state["followups"] = parsed.get("followups") or []
  state["anomaly_flags"] = parsed.get("anomalies") or []
  state["sensitive_warning"] = parsed.get("sensitive_warning")
  state["provider"] = client.provider_name
  state["model"] = client.model
 except Exception as exc:
  return {"error": f"assemble_answer failed: {exc}"}
 return state


def handle_failure(state: AgentState) -> AgentState:
 state["status"] = "failed"
 state["error"] = state.get("error") or "live_db analyst failed"
 return state


def finalize(state: AgentState) -> AgentState:
 if not state.get("status"):
  state["status"] = "completed"
 return state


def wait_for_live_db_ok() -> None:
 url = get_settings().live_db_url
 if not url:
  raise RuntimeError("Live DB unavailable")
