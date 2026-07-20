"""CSV Analyst graph nodes."""
from __future__ import annotations

import hashlib
import json
import time

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
            "history": state.get("conversation_history", [])[-8:],
            "sample_size": 3,
        })
        out = client.complete(system, user, max_tokens=1024)
        return {"plan_text": out, "error": None}
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
        return {"generated_code": out, "code_language": "sql", "error": None}
    except LLMError as exc:
        return {"error": str(exc)}


def csv_execute(state):
    try:
        sql = (state.get("generated_code") or "").strip()
        session_id = state.get("session_id")
        if not sql:
            raise ValueError("Empty generated query.")
        if not session_id:
            raise ValueError("Missing session_id.")
        rows, latency_ms, result_hash = execute_sql(str(session_id), sql)
        return {
            "rows": rows,
            "row_count": len(rows),
            "latency_ms": latency_ms,
            "result_hash": result_hash,
            "source": "duckdb",
            "error": None,
        }
    except Exception as exc:
        return {"error": str(exc), "generated_code": state.get("generated_code")}


def csv_explain(state):
    try:
        client = LLMClient()
        system = load_prompt("csv_explain")
        user = json.dumps({
            "question": state.get("input_text"),
            "plan": state.get("plan_text"),
            "code": state.get("generated_code"),
            "rows": (state.get("rows") or [])[:200],
            "row_count": state.get("row_count"),
            "latency_ms": state.get("latency_ms"),
            "result_hash": state.get("result_hash"),
        })
        out = client.complete(system, user, max_tokens=2048)
        return {"output_text": out, "error": None}
    except LLMError as exc:
        return {"error": str(exc)}


def csv_finalize(state):
    return {"status": "completed"}


def csv_error(state):
    return {"status": "failed", "output_text": None, "error": state.get("error")}
