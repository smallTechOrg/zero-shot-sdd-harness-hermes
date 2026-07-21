"""QueryRun model — one NL question execution."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models import Base


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class QueryRun(Base):
    """One NL-question run against a datasource."""

    __tablename__ = "query_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    datasource_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_columns: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluate_score: Mapped[float | None]
    iteration_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    chart_urls: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_urls: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
