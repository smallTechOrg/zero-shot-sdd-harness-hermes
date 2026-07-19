"""Phase-3 endpoint — per-run timing timeline.

Reads ``answer_runs.timeline_json`` and returns the JSON list. The
timeline is captured by the graph runner (each node appends an entry);
the runner persists it on the audit row via the Phase-3 migration.

This endpoint is read-only on the audit DB; it does NOT touch MSSQL or
the Gemini API. Setting up the runner + scheduling to also persist
``result_columns_json`` from /api/ask goes through here.
"""

from __future__ import annotations

import json

from fastapi import APIRouter

from mssql_analyst.api._common import api_error, ok
from mssql_analyst.config.settings import get_settings
from mssql_analyst.db.models import AnswerRun
from mssql_analyst.db.session import create_db_session
from mssql_analyst.observability.events import configure_logging, get_logger

router = APIRouter(tags=["phase3"])


@router.get("/api/runs/{run_id}/timeline")
def run_timeline(run_id: str) -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.phase3.timeline")

    with create_db_session() as session:
        run = session.get(AnswerRun, run_id)
        if run is None:
            raise api_error(
                "ask_not_found", f"no run with id {run_id}", status_code=404
            )
        raw = run.timeline_json or "[]"
        try:
            timeline = json.loads(raw)
        except json.JSONDecodeError:
            timeline = []
        # Map SQLAlchemy row to a JSONable dict.
        body = {
            "data": {
                "run_id": run.id,
                "status": run.status or "unknown",
                "tokens_used": int(run.tokens_used or 0),
                "sql_attempts": int(run.sql_attempts or 0),
                "latency_ms": int(run.latency_ms or 0),
                "timeline": timeline,
                "node_count": len(timeline),
            },
            "error": None,
        }
    log.info(
        "timeline",
        run_id=run_id,
        node_count=body["data"]["node_count"],
        status=body["data"]["status"],
    )
    return body
