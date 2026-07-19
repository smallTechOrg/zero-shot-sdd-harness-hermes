"""Phase-2 endpoints: history, daily rollup, CSV export, anomalies.

New routes (kept independent of the Phase-1 ``ask`` route):
  - GET /api/history?limit=N&offset=M             (newest-first paging)
  - GET /api/usage/by-day?days=14                 (per-UTC-day rollup)
  - GET /api/ask/{run_id}/csv                     (streams the result as CSV)
  - GET /api/ask/{run_id}/anomalies               (returns flagged row indices)

All four endpoints operate on data already in ``answer_runs`` — they do
not touch Microsoft SQL Server; that is the point of the Phase-2 columns.
"""

from __future__ import annotations

import json
import math

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from mssql_analyst.api._common import api_error, ok
from mssql_analyst.config.settings import get_settings
from mssql_analyst.db.models import AnswerRun
from mssql_analyst.db.session import create_db_session
from mssql_analyst.domain.phase2 import (
    HistoryResponse,
    HistoryRow,
    UsageByDayResponse,
    UsageDayBucket,
)
from mssql_analyst.observability.events import configure_logging, get_logger
from mssql_analyst.tools.anomaly import anomaly_zscore
from mssql_analyst.tools.csv_export import to_csv

router = APIRouter(tags=["phase2"])


# ---------------------------------------------------------------------------
# /api/history
# ---------------------------------------------------------------------------


@router.get("/api/history")
def history(limit: int = 50, offset: int = 0) -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.phase2.history")

    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    with create_db_session() as session:
        total = session.query(AnswerRun).count()
        rows = (
            session.query(AnswerRun)
            .order_by(AnswerRun.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            HistoryRow(
                id=r.id,
                question=r.question,
                sql=r.sql_template or "",
                status=r.status or "unknown",
                row_count=int(r.row_count or 0),
                tokens_used=int(r.tokens_used or 0),
                latency_ms=int(r.latency_ms or 0),
                created_at=r.created_at,
            )
            for r in rows
        ]

    body = HistoryResponse(limit=limit, offset=offset, total=total, rows=items)
    log.info("history", limit=limit, offset=offset, total=total, returned=len(items))
    return ok(body.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# /api/usage/by-day
# ---------------------------------------------------------------------------


@router.get("/api/usage/by-day")
def usage_by_day(days: int = 14) -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.phase2.usage_by_day")

    days = max(1, min(int(days), 90))

    with create_db_session() as session:
        # SQLite-friendly aggregation. ``day`` is a precomputed ISO yyyy-mm-dd
        # column populated on every /api/ask, so this query is indexable as
        # a simple group-by without needing strftime.
        rows = (
            session.query(
                AnswerRun.day,
            )
            .all()
        )
        # Aggregate in Python (kept tiny; the audit log has at most a few
        # hundred rows per day for a single-user local tool).
        from collections import defaultdict

        per_day_tokens: dict[str, int] = defaultdict(int)
        per_day_questions: dict[str, int] = defaultdict(int)
        # We need tokens_used too; do a second query for clarity.
        token_rows = session.query(AnswerRun.day, AnswerRun.tokens_used).all()
        for d, t in token_rows:
            per_day_tokens[d] += int(t or 0)
            per_day_questions[d] += 1

        # Sort descending by day (newest first); take top N.
        sorted_days = sorted(per_day_tokens.keys(), reverse=True)[:days]
        out = [
            UsageDayBucket(
                day=d,
                tokens=per_day_tokens[d],
                questions=per_day_questions[d],
            )
            for d in sorted_days
            if d != "1970-01-01"
        ]

    body = UsageByDayResponse(days=out)
    log.info("usage_by_day", days=days, returned=len(out))
    return ok(body.model_dump())


# ---------------------------------------------------------------------------
# /api/ask/{run_id}/csv
# ---------------------------------------------------------------------------


@router.get("/api/ask/{run_id}/csv")
def ask_csv(run_id: str):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.phase2.csv")

    with create_db_session() as session:
        run = session.get(AnswerRun, run_id)
        if run is None:
            raise api_error("ask_not_found", f"no run with id {run_id}", status_code=404)
        if (run.status or "") != "completed":
            raise api_error(
                "ask_not_completed",
                f"run {run_id} is {run.status}; nothing to export",
                status_code=404,
            )
        columns = json.loads(run.result_columns_json or "[]")
        rows = json.loads(run.result_rows_json or "[]")
        # ``rows_json`` is a list-of-lists (serialized in the ask route).
        body_csv = to_csv(columns, rows)

    log.info("csv_export", run_id=run_id, columns=len(columns), rows=len(rows))
    return PlainTextResponse(
        content=body_csv,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="mssql-{run_id}.csv"'},
    )


# ---------------------------------------------------------------------------
# /api/ask/{run_id}/anomalies
# ---------------------------------------------------------------------------


@router.get("/api/ask/{run_id}/anomalies")
def ask_anomalies(
    run_id: str,
    threshold: float = 2.0,
) -> dict:
    if not math.isfinite(threshold) or threshold <= 0:
        raise api_error("invalid_threshold", "threshold must be a positive finite number")

    with create_db_session() as session:
        run = session.get(AnswerRun, run_id)
        if run is None:
            raise api_error("ask_not_found", f"no run with id {run_id}", status_code=404)
        if (run.status or "") != "completed":
            raise api_error(
                "ask_not_completed",
                f"run {run_id} is {run.status}; nothing to score",
                status_code=404,
            )
        columns = json.loads(run.result_columns_json or "[]")
        rows = json.loads(run.result_rows_json or "[]")
        flagged = anomaly_zscore(columns, rows, threshold=threshold)

    body = {
        "run_id": run_id,
        "threshold": float(threshold),
        "flagged_rows": flagged,
        "flagged_count": len(flagged),
    }
    return ok(body)
