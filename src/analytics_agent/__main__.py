import sys

from analytics_agent.api import create_app
from analytics_agent.observability.events import configure_logging, get_logger

logger = get_logger("__main__")


def main() -> None:
    configure_logging()
    port = _resolve_port()
    if "--selftest" in sys.argv:
        _selftest()
        return
    import uvicorn

    logger.info("server.start", port=port)
    uvicorn.run("analytics_agent.api:app", host="127.0.0.1", port=port)


def _resolve_port() -> int:
    from analytics_agent.config.settings import get_settings

    return get_settings().port


def _selftest() -> None:
    """Boot-free smoke: import graph, run pipeline once, assert a snapshot was written."""
    from analytics_agent.db.session import create_db_session
    from analytics_agent.graph.runner import run_pipeline
    from analytics_agent.db.models import Snapshot

    snap = run_pipeline("#local")
    assert snap.signup > 0, "pipeline produced empty funnel"
    with create_db_session() as s:
        rows = s.query(Snapshot).filter(Snapshot.entity == "#local").all()
        assert rows, "no snapshot persisted"
    logger.info("selftest.ok", signup=snap.signup, sample=snap.sample)
    print(f"SELFTEST OK — signup={snap.signup} sample={snap.sample} snapshots={len(rows)}")


if __name__ == "__main__":
    main()
