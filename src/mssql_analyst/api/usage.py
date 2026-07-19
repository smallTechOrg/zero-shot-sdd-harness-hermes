"""`GET /api/usage` — running totals + the most-recent questions."""

from __future__ import annotations

from fastapi import APIRouter

from mssql_analyst.api._common import ok
from mssql_analyst.config.settings import get_settings
from mssql_analyst.db.models import AnswerRun
from mssql_analyst.db.session import create_db_session
from mssql_analyst.domain.usage import UsageQuestion, UsageResponse
from mssql_analyst.observability.events import configure_logging, get_logger

router = APIRouter(tags=["usage"])


@router.get("/api/usage")
def usage() -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("mssql_analyst.api.usage")

    with create_db_session() as session:
        rows = (
            session.query(AnswerRun)
            .order_by(AnswerRun.created_at.desc())
            .limit(5)
            .all()
        )
        total_q = session.query(AnswerRun).count()
        total_tokens = (
            session.query(AnswerRun.tokens_used).all()
        )
        total_tokens = sum(int(t[0] or 0) for t in total_tokens)
        total_rows = (
            session.query(AnswerRun.row_count).all()
        )
        total_rows_returned = sum(int(r[0] or 0) for r in total_rows)

    last = [
        UsageQuestion(
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
    body = UsageResponse(
        total_questions=total_q,
        total_tokens=total_tokens,
        total_rows_returned=total_rows_returned,
        last_questions=last,
    )
    log.info(
        "usage", total_questions=total_q, total_tokens=total_tokens
    )
    return ok(body.model_dump(mode="json"))
