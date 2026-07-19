"""SQLAlchemy 2.0 ORM — audit log only (one row per `/api/ask`)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Single declarative base — Alembic's ``target_metadata`` reads it."""


class AnswerRun(Base):
    """One row per question asked, with final status written on completion."""

    __tablename__ = "answer_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sql_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sql_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    # Phase-2 columns (Phase-2 migration `0002_phase2.py`):
    # JSON dump of the rows returned by the bounded SELECT; used by csv export.
    result_columns_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON dump of the rows returned by the bounded SELECT; used by csv export.
    result_rows_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # UTC day (ISO yyyy-mm-dd); precomputed for the daily rollup query.
    day: Mapped[str] = mapped_column(String, nullable=False, default="1970-01-01")
    # Phase-3 column (migration `0003_phase3.py`):
    # JSON dump of the per-node timing list [{node, started_ms, duration_ms}, ...].
    timeline_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
