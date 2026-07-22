"""SQLAlchemy 2.0 declarative models (Mapped types)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import TIMESTAMP, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
 return str(uuid4())


def _now() -> datetime:
 return datetime.now(timezone.utc)


class Base(DeclarativeBase):
 pass


class RunRow(Base):
 """One agent run: input -> output, with status + error for observability."""

 __tablename__ = "runs"

 id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
 status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
 input_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
 instruction: Mapped[str] = mapped_column(Text, nullable=False, default="")
 output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
 provider: Mapped[str | None] = mapped_column(Text, nullable=True)
 model: Mapped[str | None] = mapped_column(Text, nullable=True)
 error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
 created_at: Mapped[datetime] = mapped_column(
  TIMESTAMP(timezone=True), nullable=False, default=_now
 )
 updated_at: Mapped[datetime] = mapped_column(
  TIMESTAMP(timezone=True), nullable=False, default=_now, onupdate=_now
 )


class CSVUploadRow(Base):
 """One uploaded CSV file registered for analysis."""

 __tablename__ = "csv_uploads"

 id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
 file_name: Mapped[str] = mapped_column(Text, nullable=False)
 row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
 columns: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
 schema_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
 created_at: Mapped[datetime] = mapped_column(
  TIMESTAMP(timezone=True), nullable=False, default=_now
 )


class AuditRow(Base):
 """Append-only audit row for analyst queries."""

 __tablename__ = "audit_rows"

 id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
 run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
 user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
 question: Mapped[str] = mapped_column(Text, nullable=False)
 sql: Mapped[str | None] = mapped_column(Text, nullable=True)
 tables_touched: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
 row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
 latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
 token_usage: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON object
 created_at: Mapped[datetime] = mapped_column(
  TIMESTAMP(timezone=True), nullable=False, default=_now
 )
