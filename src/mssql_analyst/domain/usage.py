"""Response shape for `GET /api/usage`."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UsageQuestion(BaseModel):
    """One row of the last-50 (one row for Phase 1)."""

    id: str
    question: str
    sql: str
    status: str
    row_count: int
    tokens_used: int
    latency_ms: int
    created_at: datetime


class UsageResponse(BaseModel):
    total_questions: int
    total_tokens: int
    total_rows_returned: int
    last_questions: list[UsageQuestion]
