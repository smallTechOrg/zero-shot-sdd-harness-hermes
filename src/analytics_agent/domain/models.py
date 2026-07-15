from pydantic import BaseModel

from analytics_agent.db.models import FUNNEL_STAGES


class SourceRecord(BaseModel):
    """One normalized signal: a source contributed `count` to a funnel `stage`."""

    source: str
    stage: str
    count: int

    def validate_stage(self) -> "SourceRecord":
        if self.stage not in FUNNEL_STAGES:
            raise ValueError(f"unknown funnel stage: {self.stage!r}")
        return self


class Snapshot(BaseModel):
    entity: str
    sample: bool
    visit_or_install: int
    signup: int
    activated: int
    retained: int
    revenue: float
    insight: str | None = None


class FunnelPoint(BaseModel):
    entity: str
    sample: bool
    signup: int
    activated: int
    retained: int
    revenue: float


class ConnectorStatus(BaseModel):
    id: str
    name: str
    configured: bool
    env_var: str


class SetupStep(BaseModel):
    title: str
    detail: str
