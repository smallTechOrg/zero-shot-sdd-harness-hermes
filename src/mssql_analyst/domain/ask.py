"""Request/response shapes for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Incoming payload — `question` only in Phase 1."""

    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    """Successful-response data envelope."""

    run_id: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    sql_attempts: int
    latency_ms: int
    tokens_used: int
    status: str  # "completed" | "failed"
