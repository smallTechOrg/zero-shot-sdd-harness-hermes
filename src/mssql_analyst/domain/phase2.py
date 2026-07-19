"""Domain — Phase-2 response shapes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HistoryRow(BaseModel):
    id: str
    question: str
    sql: str
    status: str
    row_count: int
    tokens_used: int
    latency_ms: int
    created_at: datetime


class HistoryResponse(BaseModel):
    limit: int
    offset: int
    total: int
    rows: list[HistoryRow]


class UsageDayBucket(BaseModel):
    day: str  # ISO yyyy-mm-dd
    tokens: int
    questions: int


class UsageByDayResponse(BaseModel):
    days: list[UsageDayBucket]


class AskRunIdError(BaseModel):
    code: str
    message: str
