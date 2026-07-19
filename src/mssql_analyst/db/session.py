"""SQLAlchemy engine + session factory for the SQLite audit log."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from mssql_analyst.config.settings import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _build_engine() -> Engine:
    s = get_settings()
    url = s.database_url
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, echo=False, future=True, connect_args=connect_args)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency-style."""
    Session_ = get_session_factory()
    with Session_() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def create_db_session() -> Generator[Session, None, None]:
    """Standalone — for graph nodes, scripts, and tests."""
    Session_ = get_session_factory()
    with Session_() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db() -> None:
    """Create audit-log tables if missing. Idempotent."""
    from mssql_analyst.db.models import Base

    Base.metadata.create_all(bind=get_engine())


def reset_engine() -> None:
    """Test-only — drop the engine so the next call rebuilds it."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def dispose_engine() -> None:
    reset_engine()
