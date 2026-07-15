from uuid import uuid4

from analytics_agent.db.models import Snapshot
from analytics_agent.db.session import create_db_session
from analytics_agent.graph.agent import analytics_graph
from analytics_agent.graph.state import PipelineState
from analytics_agent.observability.events import get_logger

logger = get_logger("runner")


def run_pipeline(entity: str = "#local") -> Snapshot:
    """Run the full analytics pipeline for `entity` and return the latest Snapshot."""
    init_db_if_needed()
    initial: PipelineState = {"entity": entity, "run_id": str(uuid4()), "error": None}
    final = analytics_graph.invoke(initial)
    if final.get("status") == "failed":
        logger.error("pipeline.failed", error=final.get("error"))
    snap = final.get("snapshot")
    if snap is None:
        raise RuntimeError("pipeline produced no snapshot")
    return snap


def init_db_if_needed() -> None:
    from analytics_agent.db.session import init_db

    init_db()
