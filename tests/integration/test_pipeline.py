import pytest

from analytics_agent.db.models import FunnelPoint, Snapshot, SourceRecord
from analytics_agent.db.session import create_db_session, get_session
from analytics_agent.graph.runner import run_pipeline


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
    from analytics_agent.config.settings import get_settings

    get_settings()
    engine = create_engine(url)
    from analytics_agent.db.models import Base

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "_engine", engine)
    monkeypatch.setattr(session_module, "_SessionLocal", factory)
    monkeypatch.setattr(session_module, "init_db", lambda: None)
    yield engine
    engine.dispose()


def test_pipeline_runs_end_to_end_sample_mode(_isolated_db):
    snap = run_pipeline("#local")
    assert snap is not None
    assert snap.signup > 0
    assert snap.sample is True
    # monotonic funnel
    vals = [snap.visit_or_install, snap.signup, snap.activated, snap.retained, snap.revenue]
    assert vals == sorted(vals, reverse=True)


def test_pipeline_persists_snapshot_and_source_audit(_isolated_db):
    run_pipeline("#local")
    with create_db_session() as s:
        snaps = s.query(Snapshot).filter(Snapshot.entity == "#local").all()
        records = s.query(SourceRecord).filter(SourceRecord.entity == "#local").all()
        assert len(snaps) == 1
        assert len(records) >= 1  # sample adapter writes one record per stage


def test_refresh_appends_funnel_point(_isolated_db):
    run_pipeline("#local")
    run_pipeline("#local")
    with create_db_session() as s:
        points = s.query(FunnelPoint).filter(FunnelPoint.entity == "#local").all()
        assert len(points) == 2


def test_connectors_all_unconfigured_without_keys(_isolated_db):
    from analytics_agent.tools.connectors.hub import ConnectorHub

    hub = ConnectorHub()
    statuses = hub.statuses()
    assert len(statuses) == 7
    assert all(not c.configured for c in statuses)


def test_setup_guide_returns_steps(_isolated_db):
    from analytics_agent.tools.connectors.hub import ConnectorHub

    hub = ConnectorHub()
    steps = hub.setup_guide("ga4")
    assert len(steps) >= 3
    assert hub.setup_guide("nope") == []
