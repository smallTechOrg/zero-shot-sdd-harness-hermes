from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.types import TIMESTAMP as Timestamp
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

FUNNEL_STAGES = [
    "visit_or_install",
    "signup",
    "activated",
    "retained",
    "revenue",
]


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SourceRecord(Base):
    """Raw audit trail of one source pull for one funnel stage."""

    __tablename__ = "source_records"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    captured_at: Mapped[datetime] = mapped_column(
        Timestamp(timezone=True), nullable=False, default=_now
    )


class Snapshot(Base):
    """Cached aggregate of the latest pipeline run."""

    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    sample: Mapped[bool] = mapped_column(default=True)
    visit_or_install: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signup: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retained: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        Timestamp(timezone=True), nullable=False, default=_now
    )


class FunnelPoint(Base):
    """Time-series point (one per pipeline run) for trend charts."""

    __tablename__ = "funnel_points"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_uuid)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    sample: Mapped[bool] = mapped_column(default=True)
    signup: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retained: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        Timestamp(timezone=True), nullable=False, default=_now
    )
