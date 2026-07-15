from analytics_agent.tools.aggregate import aggregate
from analytics_agent.domain.models import SourceRecord
from analytics_agent.db.models import FUNNEL_STAGES


def test_aggregate_sums_stages_and_is_monotonic():
    records = [
        SourceRecord(source="sample", stage="visit_or_install", count=10000),
        SourceRecord(source="sample", stage="signup", count=2000),
        SourceRecord(source="sample", stage="activated", count=900),
        SourceRecord(source="sample", stage="retained", count=500),
        SourceRecord(source="sample", stage="revenue", count=200),
    ]
    snap = aggregate(records, "#local", sample=True)
    # monotonic non-increasing
    vals = [snap.visit_or_install, snap.signup, snap.activated, snap.retained, snap.revenue]
    assert vals == sorted(vals, reverse=True)
    assert snap.signup == 2000
    assert snap.activated == 900


def test_aggregate_enforces_decreasing_when_input_violates_it():
    # If a downstream stage reports more than upstream, it must be capped.
    records = [
        SourceRecord(source="sample", stage="visit_or_install", count=1000),
        SourceRecord(source="sample", stage="signup", count=5000),  # impossible
    ]
    snap = aggregate(records, "#local", sample=True)
    assert snap.signup <= snap.visit_or_install
