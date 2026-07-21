"""Runs API — POST /runs executes the agent; GET /runs/{id} fetches a run."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.db.models import RunRow
from src.db.session import get_session
from src.domain import RunResult
from src.graph.runner import run_agent
from src.summarizer import summarize_files


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
async def create_run(
    instruction: str = Form(default="Summarize the data and answer the question."),
    files: List[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
) -> dict:
    if not instruction or not instruction.strip():
        raise api_error("validation_error", "instruction is required", 400)
    if not files:
        raise api_error("validation_error", "upload at least one CSV/JSON file", 400)
    if len(files) > 12:
        raise api_error("validation_error", "maximum 12 files per run", 400)

    prepared_inputs: list[tuple[str, bytes]] = []
    total_bytes = 0
    for f in files:
        raw = await f.read()
        total_bytes += len(raw)
        prepared_inputs.append((f.filename or "upload", raw))
    if total_bytes > 5_000_000:
        raise api_error("validation_error", f"total input exceeds 5MB ({total_bytes} bytes)", 400)

    input_text, file_count = summarize_files(
        [n for n, _ in prepared_inputs],
        [c for _, c in prepared_inputs],
    )

    run_id = run_agent(input_text, instruction.strip(), file_count=file_count)
    run = session.get(RunRow, run_id)
    if run is None:  # pragma: no cover — write happened in run_agent
        raise api_error("run_not_found", f"run {run_id} vanished", 500)
    if run.status == "failed":
        return ok(_to_result(run).model_dump())
    return ok(_to_result(run).model_dump())


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("run_not_found", f"no run with id {run_id}", 404)
    return ok(_to_result(run).model_dump())
