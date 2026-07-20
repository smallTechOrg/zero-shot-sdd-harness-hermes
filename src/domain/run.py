"""Request/response models for the runs API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=100_000)


class RunResult(BaseModel):
    run_id: str
    status: str
    output_text: str | None = None
    provider: str | None = None
    model: str | None = None
    error_message: str | None = None