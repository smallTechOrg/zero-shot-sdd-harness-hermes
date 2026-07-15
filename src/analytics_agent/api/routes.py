from fastapi import APIRouter, Query

from analytics_agent.api._common import api_error, ok
from analytics_agent.db.models import FUNNEL_STAGES
from analytics_agent.db.session import create_db_session
from analytics_agent.graph.runner import run_pipeline
from analytics_agent.tools.connectors.hub import ConnectorHub

router = APIRouter()


def _latest_snapshot_dict(entity: str):
    """Return the latest Snapshot as a plain dict, serialized inside the session."""
    from sqlalchemy import select
    from analytics_agent.db.models import Snapshot

    with create_db_session() as s:
        row = s.execute(
            select(
                Snapshot.entity,
                Snapshot.sample,
                Snapshot.visit_or_install,
                Snapshot.signup,
                Snapshot.activated,
                Snapshot.retained,
                Snapshot.revenue,
                Snapshot.insight,
            )
            .where(Snapshot.entity == entity)
            .order_by(Snapshot.created_at.desc())
            .limit(1)
        ).mappings().first()
        if row is None:
            return None
        return dict(row)


@router.get("/api/funnel")
def get_funnel(entity: str = "#local") -> dict:
    row = _latest_snapshot_dict(entity)
    if row is None:
        run_pipeline(entity)
        row = _latest_snapshot_dict(entity)
    stages = [{"stage": st, "count": row[st]} for st in FUNNEL_STAGES]
    return ok(
        {
            "entity": row["entity"],
            "sample": row["sample"],
            "stages": stages,
            "insight": row["insight"],
        }
    )


@router.get("/api/kpis")
def get_kpis(entity: str = "#local") -> dict:
    row = _latest_snapshot_dict(entity)
    if row is None:
        run_pipeline(entity)
        row = _latest_snapshot_dict(entity)
    retention_pct = (100.0 * row["retained"] / row["signup"]) if row["signup"] else 0.0
    return ok(
        {
            "signups": row["signup"],
            "activated": row["activated"],
            "retention_pct": round(retention_pct, 1),
            "revenue": row["revenue"],
        }
    )


@router.get("/api/snapshots")
def get_snapshots(entity: str = "#local") -> dict:
    from sqlalchemy import select
    from analytics_agent.db.models import FunnelPoint

    with create_db_session() as s:
        rows = (
            s.execute(
                select(FunnelPoint)
                .where(FunnelPoint.entity == entity)
                .order_by(FunnelPoint.created_at.asc())
            )
            .scalars()
            .all()
        )
        points = [
            {
                "created_at": p.created_at.isoformat(),
                "sample": p.sample,
                "signup": p.signup,
                "activated": p.activated,
                "retained": p.retained,
                "revenue": p.revenue,
            }
            for p in rows
        ]
    return ok(points)


@router.get("/api/connectors")
def get_connectors() -> dict:
    hub = ConnectorHub()
    return ok([c.model_dump() for c in hub.statuses()])


@router.get("/api/setup_guide")
def get_setup_guide(source: str = Query(...)) -> dict:
    hub = ConnectorHub()
    steps = hub.setup_guide(source)
    if not steps:
        raise api_error("unknown_source", f"no setup guide for {source!r}", status_code=404)
    return ok([s.model_dump() for s in steps])


@router.post("/api/refresh")
def post_refresh(entity: str = "#local") -> dict:
    run_pipeline(entity)
    return get_funnel(entity)
