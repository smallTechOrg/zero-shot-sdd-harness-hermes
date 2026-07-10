"""Pydantic request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    hosts: list[str] = Field(min_length=2, max_length=3)


class GenerateResponse(BaseModel):
    session_id: str
    status: str
