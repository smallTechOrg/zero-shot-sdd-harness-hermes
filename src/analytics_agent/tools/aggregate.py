from analytics_agent.db.models import FUNNEL_STAGES
from analytics_agent.domain.models import (
    FunnelPoint,
    Snapshot,
    SourceRecord,
)


def aggregate(records: list[SourceRecord], entity: str, sample: bool) -> Snapshot:
    """Sum each funnel stage across all sources, enforce monotonic decreasing order."""
    totals: dict[str, int] = {stage: 0 for stage in FUNNEL_STAGES}
    revenue_amount = 0.0
    for rec in records:
        if rec.stage not in totals:
            continue
        totals[rec.stage] += rec.count
        if rec.stage == "revenue":
            # revenue records carry a dollar amount in `count` as a float-in-int stand-in
            revenue_amount += float(rec.count)

    # Enforce monotonic non-increasing down the funnel (blended correctness).
    capped = totals[FUNNEL_STAGES[0]]
    ordered: dict[str, int] = {}
    for stage in FUNNEL_STAGES:
        capped = min(capped, totals[stage])
        ordered[stage] = capped

    return Snapshot(
        entity=entity,
        sample=sample,
        visit_or_install=ordered["visit_or_install"],
        signup=ordered["signup"],
        activated=ordered["activated"],
        retained=ordered["retained"],
        revenue=revenue_amount if revenue_amount else float(ordered["revenue"]),
    )


def to_funnel_point(snap: Snapshot) -> FunnelPoint:
    return FunnelPoint(
        entity=snap.entity,
        sample=snap.sample,
        signup=snap.signup,
        activated=snap.activated,
        retained=snap.retained,
        revenue=snap.revenue,
    )
