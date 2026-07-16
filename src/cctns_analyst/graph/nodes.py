"""LangGraph nodes for the CCTNS analyst agent.

Each node is a function ``(state) -> partial state`` that returns *only* the
keys it sets or mutates. The graph runner merges them.

LLM nodes call into ``cctns_analyst.llm.client.LLMClient``; they never call
provider SDKs directly. The mirror node calls into
``cctns_analyst.tools.cctns_mirror`` so the executor can be swapped (live vs.
mock) without touching the graph.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from cctns_analyst.graph.state import AgentState
from cctns_analyst.llm.client import LLMClient
from cctns_analyst.prompts.loader import load_prompt

logger = logging.getLogger("cctns_analyst.graph.nodes")

MAX_SAMPLE_ROWS = 100  # rows we send to the LLM (data-locality block)


def nl_to_sql(
    state: AgentState,
    *,
    llm: LLMClient,
    schema_provider: Callable[[], dict[str, list[dict[str, str]]]],
) -> AgentState:
    """Draft a single SELECT against the cctns_mirror schema.

    State in : question, request_id, sql_attempts, validation_error.
    State out: sql, sql_attempts, error.
    """
    q = (state.get("question") or "").strip()
    if not q:
        return {"error": "empty_question", "status": "failed"}

    schema = schema_provider()
    template = load_prompt("nl_to_sql")
    user_payload = {
        "schema": schema,
        "question": q,
        # validator feedback, if any (only present on the retry)
        "previous_sql": state.get("sql"),
        "validation_error": state.get("validation_error"),
    }

    try:
        sql_text = llm.complete_json(
            prompt_name="nl_to_sql",
            template=template,
            user_payload=user_payload,
        )
    except Exception as exc:  # noqa: BLE001 — propagate via state, never raise into graph
        return _capture(state, exc, where="nl_to_sql")

    sql = (sql_text or {}).get("sql") if isinstance(sql_text, dict) else sql_text
    sql = (sql or "").strip()
    # Increment attempts only if we made a real attempt. We treat the very first
    # call as attempt 1; any retry routed by the validator increments via the
    # validator.
    attempts = int(state.get("sql_attempts") or 0) + 1

    if not sql:
        return {
            "sql": None,
            "sql_attempts": attempts,
            "error": "llm_returned_empty_sql",
            "status": "failed",
        }

    return {
        "sql": sql,
        "sql_attempts": attempts,
        "validation_error": None,
    }


def execute_sql(
    state: AgentState,
    *,
    mirror_runner: Callable[[str], tuple[list[str], list[tuple], int]],
    row_cap: int,
) -> AgentState:
    """Run the SQL on the mirror with strict bounds."""
    sql = state.get("sql") or ""
    if not sql:
        return {"error": "no_sql", "status": "failed"}
    try:
        t0 = time.perf_counter()
        columns, rows, raw_count = mirror_runner(sql)
        # Always enforce the cap server-side, regardless of what the mirror returned.
        if len(rows) > row_cap:
            rows = rows[:row_cap]
        # NOTE: latency_ms here is *only* the executor's wall time. The runner
        # adds the LLM latency on finalize.
        exec_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "columns": list(columns),
            "rows": rows,
            "row_count": int(raw_count),
            "latency_ms": int(state.get("latency_ms") or 0) + exec_ms,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": _public_message(exc), "status": "failed"}


def validate_result(state: AgentState) -> AgentState:
    """Validate the bounded result. Empty results pass.

    A failed validation sets ``validation_error`` so the next edges cycle
    the graph back to ``nl_to_sql`` (one retry, via the attempts cap).
    """
    rows = state.get("rows") or []
    if not rows:
        # Empty result is allowed. The summariser is told about it.
        return {"validation_error": None}
    cols = state.get("columns") or []
    if not cols:
        return {"validation_error": "result_has_no_columns"}
    if not all(isinstance(r, tuple) for r in rows):
        return {"validation_error": "rows_must_be_tuples"}
    if any(len(r) != len(cols) for r in rows):
        return {"validation_error": "row_arity_mismatch"}
    return {"validation_error": None}


def summarize_answer(
    state: AgentState,
    *,
    llm: LLMClient,
) -> AgentState:
    """Turn the bounded result into a short prose answer."""
    q = state.get("question") or ""
    cols = state.get("columns") or []
    rows = (state.get("rows") or [])[:MAX_SAMPLE_ROWS]
    raw_count = state.get("row_count") or 0
    template = load_prompt("summarize")

    user_payload = {
        "question": q,
        "columns": cols,
        "rows": [_serialise_row(r) for r in rows],
        "row_count": raw_count,
        "result_was_truncated": raw_count > MAX_SAMPLE_ROWS,
    }

    try:
        out = llm.complete_json(
            prompt_name="summarize",
            template=template,
            user_payload=user_payload,
        )
    except Exception as exc:  # noqa: BLE001
        return _capture(state, exc, where="summarize_answer")

    answer = (out or {}).get("answer") if isinstance(out, dict) else out
    answer = (answer or "").strip()
    if not answer:
        return {"error": "llm_returned_empty_answer", "status": "failed"}

    return {"answer": answer}


def handle_error(state: AgentState) -> AgentState:
    """Terminal node — make sure the partial graph state is recoverable."""
    return {
        "status": "failed",
        "error": state.get("error") or "unknown_failure",
    }


def finalize(state: AgentState) -> AgentState:
    """Terminal node — confirm completion if no error was raised earlier."""
    if state.get("status") == "failed":
        return {"status": "failed"}
    return {"status": "completed"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _capture(state: AgentState, exc: Exception, *, where: str) -> dict[str, Any]:
    """Capture an exception onto the state without ever raising again."""
    logger.warning("graph_node_failed", extra={"where": where, "exc": repr(exc)})
    return {
        "error": _public_message(exc),
        "status": "failed",
        "_last_failed_node": where,
    }


def _public_message(exc: Exception) -> str:
    """Build a public message that does NOT leak `repr(exc)` (a stack trace)."""
    msg = str(exc).strip()
    if not msg:
        msg = exc.__class__.__name__
    return msg[:300]


def _serialise_row(r: tuple) -> list:
    """JSON-safe row serializer — numpy types etc. -> python primitives."""
    out = []
    for v in r:
        if hasattr(v, "item"):
            try:
                out.append(v.item())
                continue
            except Exception:  # noqa: BLE001
                pass
        out.append(v)
    return out
