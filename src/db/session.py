"""Engine + session factory. Singletons are resettable for tests."""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        from src.config.settings import get_settings

        url = get_settings().database_url
        if url.startswith("sqlite:///"):
            # Ensure the parent directory of the SQLite file exists.
            db_path = Path(url.removeprefix("sqlite:///"))
            if db_path.parent != Path("."):
                db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, echo=False)
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    with _get_session_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextmanager
def create_db_session() -> Generator[Session, None, None]:
    """Standalone — for graph nodes, CLI, scripts."""
    with _get_session_factory()() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def init_db() -> None:
 from src.db.models import Base
 import src.db.query_run as _query_run  # noqa: F401 — register QueryRun model

 Base.metadata.create_all(bind=_get_engine())
