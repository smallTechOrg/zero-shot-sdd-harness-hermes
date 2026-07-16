"""`POST /v1/answer` — the primary endpoint.

Routes through the graph runner; persists an ``AnswerRun`` row;
errors render as the JSON envelope, never raise HTTPException directly for
the SPA fetch layer (the UI handles them).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException

from cctns_analyst.api._common import error_envelope, ok
from cctns_analyst.api.dependencies import build_request_graph
from cctns_analyst.db.models import AnswerRun
from cctns_analyst.db.session import create_db_session
from cctns_analyst.domain.question import AnswerRequest
from cctns_analyst.observability.events import bind_request_context, get_logger

log = get_logger("cctns_analyst.api.answer")

router = APIRouter(tags=["answer"])


@router.post("/v1/answer")
def post_answer(req: AnswerRequest) -> dict:
    """Run one request through the agent graph and return the JSON envelope."""
    bind_request_context(request_id=None, run_id=None)
    graph = build_request_graph()

    # Persist pending row
    with create_db_session() as session:
        run = AnswerRun(
            request_id="",
            question=req.question,
            status="pending",
        )
        session.add(run)
        session.flush()
        run_id = run.id
        session.expunge(run)
    bind_request_context(run_id=run_id)

    initial: dict = {
        "request_id": "",
        "question": req.question,
        "sql": None,
        "sql_attempts": 0,
        "validation_error": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "answer": None,
        "status": "pending",
        "error": None,
        "latency_ms": 0,
    }

    try:
        final = graph.invoke(initial)
    except Exception as exc:  # noqa: BLE001 — pipeline error envelope
        log.error("pipeline_error_unhandled", error=exc.__class__.__name__)
        _finalize_run(run_id, status="failed", sql_template="", lat=0, rc=0, err=str(exc))
        raise HTTPException(
            status_code=500,
            detail=error_envelope("pipeline_error", "graph raised unexpectedly"),
        )

    status = "completed" if not final.get("error") else "failed"
    payload = {
        "answer": final.get("answer") or "",
        "sql": final.get("sql") or "",
        "columns": final.get("columns") or [],
        "rows": [list(r) for r in (final.get("rows") or [])],
        "latency_ms": int(final.get("latency_ms") or 0),
        "row_count": int(final.get("row_count") or 0),
        "sql_attempts": int(final.get("sql_attempts") or 0),
        "status": status,
    }

    if status == "failed":
        err_msg = (final.get("error") or "unknown")[:300]
        log.warning("answer_failed", error=err_msg, sql_attempts=payload["sql_attempts"])
        _finalize_run(
            run_id,
            status="failed",
            sql_template=payload["sql"],
            lat=payload["latency_ms"],
            rc=payload["row_count"],
            err=err_msg,
        )
        raise _error_for_run(final, payload)

    _finalize_run(
        run_id,
        status="completed",
        sql_template=payload["sql"],
        lat=payload["latency_ms"],
        rc=payload["row_count"],
        err=None,
    )
    log.info(
        "answer_completed",
        latency_ms=payload["latency_ms"],
        row_count=payload["row_count"],
        sql_attempts=payload["sql_attempts"],
    )
    return ok(payload)


def _error_for_run(final: dict, payload: dict) -> HTTPException:
    err = (final.get("error") or "").strip()
    if err in {"empty_question", "validation_error"}:
        return HTTPException(
            status_code=400,
            detail=error_envelope(err, err),
        )
    if err in {"no_sql", "llm_returned_empty_sql", "llm_returned_empty_answer"}:
        return HTTPException(
            status_code=502,
            detail=error_envelope("llm_failure", err),
        )
    return HTTPException(
        status_code=500,
        detail=error_envelope("pipeline_error", err or "graph failed"),
    )


def _finalize_run(run_id: str, *, status: str, sql_template: str, lat: int, rc: int, err: str | None) -> None:
    with create_db_session() as session:
        run = session.get(AnswerRun, run_id)
        if run is None:
            return
        run.status = status
        run.sql_template = sql_template or ""
        run.latency_ms = lat
        run.row_count = rc
        run.error_message = err
