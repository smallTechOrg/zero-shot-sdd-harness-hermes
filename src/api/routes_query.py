"""Query routes — POST /api/v1/query"""
from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from src.api._common import api_error, ok
from src.graph.runner import run_agent

router = APIRouter()


class QueryRequest(BaseModel):
    session_id: str | None = None
    question: str
    data_source: str = "cache"
    sources: list[str] | None = None


@router.post("/query")
def ask(req: QueryRequest) -> dict:
    if not req.question.strip():
        raise api_error("invalid_request", "question cannot be empty.", 422)
    try:
        run_id = run_agent(
            instruction=req.question,
            session_id=req.session_id,
            data_source=req.data_source,
        )
    except Exception as exc:  # pragma: no cover - harness verified path
        raise api_error("agent_error", str(exc), 500) from exc
    return ok({"run_id": run_id, "status": "queued"})
