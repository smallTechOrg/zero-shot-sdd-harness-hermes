"""Request/response models for the runs API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
 text: str = Field(..., min_length=1, max_length=100_000)
 instruction: str = Field(
 default="Summarize the text in one short paragraph.",
 min_length=1,
 max_length=2_000,
 )
 data_source: str | None = Field(
 default=None,
 pattern="^(transform|live_db|fraud_detection)$",
 )


class RunResult(BaseModel):
    run_id: str
    status: str
    output_text: str | None = None
    provider: str | None = None
    model: str | None = None
    error_message: str | None = None
