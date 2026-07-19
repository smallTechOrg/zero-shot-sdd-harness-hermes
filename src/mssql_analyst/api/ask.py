"""`POST /api/ask` — the primary endpoint.

Routes through the graph runner; persists an ``AnswerRun`` row in the audit
log; errors render as the JSON envelope, never raise ``HTTPException``
directly to a hidden stack trace.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from mssql_analyst.api._common import api_error, ok
from mssql_analyst.config.settings import get_settings
from mssql_analyst.db.models import AnswerRun
from mssql_analyst.db.session import create_db_session
from mssql_analyst.domain.ask import AskRequest
from mssql_analyst.graph.runner import run_agent
from mssql_analyst.observability.events import (
    bind_request_context,
    configure_logging,
    get_logger,
    new_request_id,
)

router = APIRouter(tags=["ask"])


@router.post("/api/ask")
def post_ask(req: AskRequest) -> dict:
    """Run one question through the agent graph and return the JSON envelope."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.ask")

    request_id = new_request_id()
    bind_request_context(request_id=request_id, run_id=None)

    question = (req.question or "").strip()
    if not question:
        log.warning("empty_question")
        raise api_error("empty_question", "question must be non-empty")

    # Persist a pending row.
    with create_db_session() as session:
        run = AnswerRun(request_id=request_id, question=question, status="pending")
        session.add(run)
        session.flush()
        run_id = run.id
        session.expunge(run)
    bind_request_context(request_id=request_id, run_id=run_id)

    t0 = time.perf_counter()
    try:
        final = run_agent(question, request_id=request_id)
    except Exception as exc:  # noqa: BLE001
        log.error("pipeline_error_unhandled", error=exc.__class__.__name__)
        _finalize_run(
            run_id,
            status="failed",
            sql_template="",
            lat=int((time.perf_counter() - t0) * 1000),
            rc=0,
            tokens=0,
            err=f"pipeline_error: {exc.__class__.__name__}",
        )
        raise api_error(
            "pipeline_error", "graph raised unexpectedly", status_code=500
        )

    # If the inner caller didn't already set latency, set ours.
    if not final.get("latency_ms"):
        final["latency_ms"] = int((time.perf_counter() - t0) * 1000)

    status = "completed" if not final.get("error") else "failed"
    payload = {
        "sql": final.get("sql") or "",
        "columns": list(final.get("columns") or []),
        "rows": [list(r) for r in (final.get("rows") or [])],
        "row_count": int(final.get("row_count") or 0),
        "sql_attempts": int(final.get("sql_attempts") or 0),
        "latency_ms": int(final.get("latency_ms") or 0),
        "tokens_used": int(final.get("tokens_used") or 0),
        "status": status,
    }

    if status == "failed":
        err_msg = (final.get("error") or "unknown")[:300]
        log.warning(
            "answer_failed",
            error=err_msg,
            sql_attempts=payload["sql_attempts"],
            row_count=payload["row_count"],
        )
        _finalize_run(
            run_id,
            status="failed",
            sql_template=payload["sql"],
            lat=payload["latency_ms"],
            rc=payload["row_count"],
            tokens=payload["tokens_used"],
            err=err_msg,
        )
        raise _error_for_run(err_msg)

    _finalize_run(
        run_id,
        status="completed",
        sql_template=payload["sql"],
        lat=payload["latency_ms"],
        rc=payload["row_count"],
        tokens=payload["tokens_used"],
        err=None,
    )
    log.info(
        "answer_completed",
        latency_ms=payload["latency_ms"],
        row_count=payload["row_count"],
        tokens_used=payload["tokens_used"],
        sql_attempts=payload["sql_attempts"],
    )
    return ok(payload)


def _error_for_run(msg: str):
    """Map a graph error string to the right HTTP code + code."""
    if msg.startswith("empty_question"):
        return api_error("empty_question", msg)
    if msg.startswith("unsafe_sql"):
        return api_error("unsafe_sql", msg)
    if msg.startswith("validation_error"):
        return api_error("validation_error", msg, status_code=400)
    if "llm_request_failed" in msg or "gemini_" in msg:
        return api_error("llm_unavailable", msg, status_code=502)
    if "mssql_" in msg or "no_db_configured" in msg:
        return api_error(
            "mssql_unavailable" if "no_db_configured" not in msg else "no_db_configured",
            msg,
            status_code=502 if "no_db_configured" not in msg else 503,
        )
    return api_error("pipeline_error", msg, status_code=500)


def _finalize_run(
    run_id: str,
    *,
    status: str,
    sql_template: str,
    lat: int,
    rc: int,
    tokens: int,
    err: str | None,
) -> None:
    with create_db_session() as session:
        run = session.get(AnswerRun, run_id)
        if run is None:
            return
        run.status = status
        run.sql_template = sql_template or ""
        run.latency_ms = int(lat or 0)
        run.row_count = int(rc or 0)
        run.tokens_used = int(tokens or 0)
        run.error_message = err
