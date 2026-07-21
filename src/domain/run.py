"""Request/response models for the runs API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    instruction: str = Field(
        default="Summarize the data and answer the question.",
        min_length=1,
        max_length=2_000,
    )


class RunResult(BaseModel):
    run_id: str
    status: str
    output_text: str | None = None
    provider: str | None = None
    model: str | None = None
    error_message: str | None = None
    file_count: int = 0
