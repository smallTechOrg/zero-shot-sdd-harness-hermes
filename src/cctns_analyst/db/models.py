"""SQLAlchemy 2.0 ORM models for the CCTNS analyst.

Mapped types only, no legacy Declarative. ``run`` tables and ``cctns_table``
metadata — raw CCTNS rows are never persisted here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, Text, TIMESTAMP, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Single declarative base — Alembic ``target_metadata`` reads it."""


class AnswerRun(Base):
    __tablename__ = "answer_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sql_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sql_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class CctnsTable(Base):
    __tablename__ = "cctns_tables"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    schema_name: Mapped[str] = mapped_column(String, nullable=False, default="cctns_mirror")
    # JSON string of [{"name":"col","type":"varchar"}, …]
    columns_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    version: Mapped[str] = mapped_column(String, nullable=False, default="v1")
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
