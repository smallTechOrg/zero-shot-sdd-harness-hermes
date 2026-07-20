"""Runs API — POST /runs executes the agent; GET /runs/{id} fetches a run."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.db.models import RunRow
from src.db.session import get_session
from src.domain import RunRequest, RunResult
from src.capabilities.tasks import run_csv_agent
from src.config.settings import get_settings
from src.llm.providers.base import LLMError

router = APIRouter()


def _to_result(run: RunRow) -> RunResult:
    return RunResult(
        run_id=run.id,
        status=run.status,
        output_text=run.output_text,
        provider=run.provider,
        model=run.model,
        error_message=run.error_message,
    )


@router.post("/runs")
def create_run(req: RunRequest, session: Session = Depends(get_session)) -> dict:
    # Create a run record
    run = RunRow(
        input_text=req.question,
        instruction="",
        status="running",
    )
    session.add(run)
    session.flush()
    run_id = run.id

    # Run the CSV agent
    try:
        result = run_csv_agent(req.session_id, req.question)
    except LLMError as exc:
        result = {"status": "failed", "output_text": None, "error": str(exc)}

    # Update the run record with the result
    run.output_text = result.get("output_text")
    run.status = result.get("status", "completed")
    if run.status == "failed":
        run.error_message = result.get("error")
    # Get provider and model from settings
    s = get_settings()
    run.provider = s.resolve_provider()
    run.model = s.resolve_model()

    session.add(run)
    session.commit()
    session.refresh(run)

    return ok(_to_result(run))


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("run_not_found", f"no run with id {run_id}", 404)
    return ok(_to_result(run))