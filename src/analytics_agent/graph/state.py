from typing import TypedDict


class PipelineState(TypedDict, total=False):
    entity: str
    run_id: str
    error: str | None
    records: list
    snapshot: object | None
    insight: str | None
    status: str
