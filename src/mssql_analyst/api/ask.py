"""`POST /api/ask` — the primary endpoint.

Routes through the graph runner; persists an ``AnswerRun`` row in the audit
log; errors render as the JSON envelope, never raise ``HTTPException``
directly to a hidden stack trace.

Phase-2: also persists the result columns + result rows (JSON) so the
``/api/ask/{run_id}/csv`` endpoint can stream the same result without
re-running the SELECT. Successful runs populate the JSON columns;
``status=failed`` runs leave them empty.
"""

from __future__ import annotations

import json
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
    pending_day = _utc_day_iso()
    with create_db_session() as session:
        run = AnswerRun(
            request_id=request_id,
            question=question,
            status="pending",
            day=pending_day,
        )
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
            columns_json="[]",
            rows_json="[]",
            day_iso=pending_day,
        )
        raise api_error(
            "pipeline_error", "graph raised unexpectedly", status_code=500
        )

    # If the inner caller didn't already set latency, set ours.
    if not final.get("latency_ms"):
        final["latency_ms"] = int((time.perf_counter() - t0) * 1000)

    status = "completed" if not final.get("error") else "failed"
    payload = {
        "run_id": run_id,
        "sql": final.get("sql") or "",
        "columns": list(final.get("columns") or []),
        "rows": [list(r) for r in (final.get("rows") or [])],
        "row_count": int(final.get("row_count") or 0),
        "sql_attempts": int(final.get("sql_attempts") or 0),
        "latency_ms": int(final.get("latency_ms") or 0),
        "tokens_used": int(final.get("tokens_used") or 0),
        "row_cap_effective": int(final.get("row_cap_effective") or 0),
        "status": status,
    }

    # Phase-3 payload fields surfaced to the user.
    timeline = list(final.get("timelines") or [])
    timeline_json = json.dumps(timeline, ensure_ascii=False)

    # Phase-2: serialize columns/rows to JSON for persistence (so CSV export
    # can serve the same data without a fresh MSSQL round-trip).
    columns_json = json.dumps(payload["columns"], ensure_ascii=False)
    rows_json = json.dumps(payload["rows"], ensure_ascii=False, default=str)

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
            columns_json="[]",
            rows_json="[]",
            day_iso=pending_day,
            timeline_json=timeline_json,
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
        columns_json=columns_json,
        rows_json=rows_json,
        day_iso=pending_day,
        timeline_json=timeline_json,
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
    columns_json: str = "[]",
    rows_json: str = "[]",
    day_iso: str = "1970-01-01",
    timeline_json: str = "[]",
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
        run.result_columns_json = columns_json or "[]"
        run.result_rows_json = rows_json or "[]"
        run.day = day_iso or "1970-01-01"
        # Phase-3: persist the per-node timing list as JSON.
        run.timeline_json = timeline_json or "[]"
        # Phase-3: round-trip the latest effective row cap from the runner
        # via run.sql_attempts / run.row_cap_effective — Phase-3 surfaces
        # this via /api/runs/{run_id}/timeline.status metadata; here we
        # only persist what was provided.


def _utc_day_iso() -> str:
    """UTC day as ISO yyyy-mm-dd (matches what `created_at.date()` would give)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).date().isoformat()
