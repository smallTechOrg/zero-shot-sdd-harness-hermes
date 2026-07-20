"""CSV Analyst graph nodes."""
from __future__ import annotations

import json
from typing import Any

from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError
from src.services.csv_exec import execute_sql


def csv_plan(state):
    try:
        client = LLMClient()
        system = load_prompt("csv_plan")
        user = json.dumps({
            "question": state.get("input_text"),
            "schema": state.get("schema_summary"),
        })
        out = client.complete(system, user, max_tokens=4096)
        return {
            "plan_text": out,
            "error": None
        }
    except LLMError as exc:
        return {"error": str(exc)}


def csv_query(state):
    try:
        client = LLMClient()
        system = load_prompt("csv_query")
        user = json.dumps({
            "question": state.get("input_text"),
            "plan": state.get("plan_text"),
            "schema": state.get("schema_summary"),
        })
        out = client.complete(system, user, max_tokens=4096)
        return {
            "generated_code": out,
            "code_language": "sql",
            "error": None
        }
    except LLMError as exc:
        return {"error": str(exc)}


def csv_execute(state):
    try:
        if not state.get("generated_code"):
            return {"error": "No SQL query to execute."}
        session_id = state.get("session_id")
        if not session_id:
            return {"error": "Session ID not found."}
        rows, latency_ms, result_hash = execute_sql(str(session_id), state.get("generated_code"))
        return {
            "rows": rows,
            "row_count": len(rows),
            "latency_ms": latency_ms,
            "result_hash": result_hash,
            "error": None
        }
    except Exception as exc:
        return {"error": str(exc)}


def csv_explain(state):
    try:
        client = LLMClient()
        system = load_prompt("csv_explain")
        user = json.dumps({
            "question": state.get("input_text"),
            "plan": state.get("plan_text"),
            "schema": state.get("schema_summary"),
            "query": state.get("generated_code"),
            "rows": (state.get("rows") or [])[:200],
        })
        out = client.complete(system, user, max_tokens=2048)
        return {"output_text": out, "error": None}
    except LLMError as exc:
        return {"error": str(exc)}


def csv_finalize(state):
    return {"status": "completed"}


def csv_error(state):
    return {"status": "failed", "output_text": None, "error": state.get("error")}