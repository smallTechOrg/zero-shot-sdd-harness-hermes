"""Request body for POST /v1/answer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    """Incoming payload — `question` only in Phase 1."""

    question: str = Field(min_length=1, max_length=2000)
