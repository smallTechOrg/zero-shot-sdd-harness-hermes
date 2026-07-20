"""Session domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    id: str
    status: str = "active"
    created_at: str
    schema_summary: dict | None = None
    turn_count: int = 0


class SessionResponse(BaseModel):
    id: str
    status: str
    created_at: str
    updated_at: str
    schema_summary: dict | None = None
    turn_count: int = 0


class CsvUploadResponse(BaseModel):
    session_id: str
    uploaded: list[str] = Field(default_factory=list)
    schema_summary: dict | None = None
    errors: list[str] = Field(default_factory=list)


class SessionRunRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=4000)


class ClarifyResponse(BaseModel):
    run_id: str
    status: str = "clarifying"
    clarify_prompt: str | None = None
    output_text: str | None = None
