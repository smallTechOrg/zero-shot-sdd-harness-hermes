import pytest

from analytics_agent.config.settings import get_settings
from analytics_agent.db.models import Base
from analytics_agent.db.session import _engine, _SessionLocal, create_db_session, init_db


@pytest.fixture(autouse=True)
def _reset_settings_singleton():
    import analytics_agent.config.settings as m

    m._settings = None
    yield
    m._settings = None


@pytest.fixture()
def _isolated_db(tmp_path, monkeypatch):
    import analytics_agent.db.session as session_module
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = f"sqlite:///{tmp_path}/test.db"
    monkeypatch.setenv("ANALYTICS_DATABASE_URL", url)
    get_settings()  # resolve with the patched env
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)
    yield
    engine.dispose()


def test_settings_singleton_resettable():
    s = get_settings()
    assert s.port == 8001


def test_models_define_three_tables():
    names = set(Base.metadata.tables.keys())
    assert {"snapshots", "funnel_points", "source_records"} <= names


def test_session_factory_returns_session():
    with create_db_session() as s:
        assert s is not None
