from analytics_agent.config.settings import Settings, get_settings
from analytics_agent.llm.client import LLMClient
from analytics_agent.observability.events import get_logger
from analytics_agent.tools.aggregate import aggregate, to_funnel_point
from analytics_agent.tools.connectors.hub import ConnectorHub

logger = get_logger("graph")

from typing import TypedDict  # noqa: E402


class PipelineState(TypedDict, total=False):
    entity: str
    run_id: str
    error: str | None
    records: list
    snapshot: object | None
    insight: str | None
    status: str


def fetch_sources(state: PipelineState) -> PipelineState:
    settings = get_settings()
    hub = ConnectorHub(settings)
    records, configured = hub.pull_all(state["entity"])
    logger.info(
        "pipeline.fetch",
        entity=state["entity"],
        records=len(records),
        real_sources=configured,
    )
    return {**state, "records": records, "error": None}


def aggregate_node(state: PipelineState) -> PipelineState:
    settings = get_settings()
    hub = ConnectorHub(settings)
    configured = any(c.is_configured() for c in hub.real)
    snap = aggregate(state["records"], state["entity"], sample=not configured)
    return {**state, "snapshot": snap, "error": None}


def compute_funnel(state: PipelineState) -> PipelineState:
    # Snapshot already computed in aggregate_node; this keeps the graph shape explicit
    # and is where future derived metrics (conversion %, deltas) would attach.
    return {**state, "error": None}


def narrate(state: PipelineState) -> PipelineState:
    client = LLMClient(get_settings())
    snap = state.get("snapshot")
    if snap is None:
        return {**state, "insight": None}
    insight = client.narrate(snap)
    return {**state, "insight": insight}


def handle_error(state: PipelineState) -> PipelineState:
    logger.error("pipeline.error", error=state.get("error"))
    return {**state, "status": "failed"}


def finalize(state: PipelineState) -> PipelineState:
    from analytics_agent.db.models import FunnelPoint as FunnelPointRow
    from analytics_agent.db.models import Snapshot as SnapshotRow
    from analytics_agent.db.models import SourceRecord as SourceRecordRow
    from analytics_agent.db.session import create_db_session
    from analytics_agent.tools.aggregate import to_funnel_point

    snap = state["snapshot"]
    insight = state.get("insight")
    entity = state["entity"]
    records = state.get("records", [])

    with create_db_session() as session:
        snap_row = SnapshotRow(
            entity=snap.entity,
            sample=snap.sample,
            visit_or_install=snap.visit_or_install,
            signup=snap.signup,
            activated=snap.activated,
            retained=snap.retained,
            revenue=snap.revenue,
            insight=insight,
        )
        session.add(snap_row)
        session.flush()
        point = to_funnel_point(snap)
        session.add(
            FunnelPointRow(
                entity=point.entity,
                sample=point.sample,
                signup=point.signup,
                activated=point.activated,
                retained=point.retained,
                revenue=point.revenue,
            )
        )
        for rec in records:
            session.add(
                SourceRecordRow(
                    entity=entity,
                    source=rec.source,
                    stage=rec.stage,
                    count=rec.count,
                )
            )
    logger.info("pipeline.finalize", entity=entity, sample=snap.sample)
    return {**state, "status": "completed"}
