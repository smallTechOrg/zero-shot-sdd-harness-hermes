"""Response shape for POST /v1/answer — the JSON payload mirroring spec/api.md."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerRunSummary(BaseModel):
    answer: str
    sql: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list] = Field(default_factory=list)
    latency_ms: int
    row_count: int
    sql_attempts: int
    status: str = "completed"
