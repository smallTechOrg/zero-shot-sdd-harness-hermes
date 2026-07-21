"""Runs API — POST /runs executes the agent; GET /runs/{id} fetches a run."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.db.models import AuditRow, RunRow
from src.db.session import get_session
from src.domain import RunRequest, RunResult
from src.graph.runner import run_agent

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
 run_id = run_agent(req.text, req.instruction)
 run = session.get(RunRow, run_id)
 if run is None: # pragma: no cover — write happened in run_agent
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


def _serialize_audit(audit: AuditRow | None) -> dict[str, Any] | None:
 if audit is None:
  return None
 return {
 "run_id": audit.run_id,
 "question": audit.question,
 "sql": audit.sql,
 "tables_touched": json.loads(audit.tables_touched) if audit.tables_touched else [],
 "row_count": audit.row_count,
 "latency_ms": audit.latency_ms,
 "token_usage": json.loads(audit.token_usage) if audit.token_usage else {},
 "created_at": audit.created_at.isoformat() if audit.created_at else None,
 }


def _serialize_run(run: RunRow) -> dict[str, Any]:
 return {
 "run_id": run.id,
 "status": run.status,
 "input_text": run.input_text,
 "instruction": run.instruction,
 "output_text": run.output_text,
 "provider": run.provider,
 "model": run.model,
 "error_message": run.error_message,
 "created_at": run.created_at.isoformat() if run.created_at else None,
 "updated_at": run.updated_at.isoformat() if run.updated_at else None,
 }


@router.get("/runs")
def list_runs(limit: int = 100, session: Session = Depends(get_session)) -> dict:
 rows = session.query(RunRow).order_by(desc(RunRow.created_at)).limit(max(1, min(limit, 500))).all()
 return ok([_serialize_run(run) for run in rows])


@router.get("/runs/{run_id}/audit")
def get_run_audit(run_id: str, session: Session = Depends(get_session)) -> dict:
 run = session.get(RunRow, run_id)
 if run is None:
  raise api_error("run_not_found", f"no run with id {run_id}", 404)
 audit = session.query(AuditRow).filter(AuditRow.run_id == run_id).order_by(desc(AuditRow.created_at)).first()
 return ok({
 "run": _serialize_run(run),
 "audit": _serialize_audit(audit),
 })
