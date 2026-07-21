"""run_agent() — unchanged signature (input_text, instruction) for baseline API.
New query entry point: run_query(initial: dict) -> dict
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.db.models import RunRow
from src.db.session import create_db_session
from src.graph.nodes import transform_text  # baseline transform slot
from src.observability.events import get_logger

log = get_logger("runner")


def run_agent(input_text: str, instruction: str) -> str:
    """Baseline transform slot — same signature that runs.py calls."""
    initial = {
        "input_text": input_text,
        "instruction": instruction,
        "error": None,
    }
    out = transform_text(initial)
    run_id = out.get("run_id") or "unknown"

    with create_db_session() as session:
        row = RunRow(
            id=run_id,
            input_text=input_text,
            instruction=instruction,
            status="completed" if not out.get("error") else "failed",
            output_text=out.get("output_text"),
            provider=out.get("provider"),
            model=out.get("model"),
            error_message=out.get("error"),
        )
        session.add(row)
        session.flush()
    return run_id


def run_query(initial: dict) -> dict:
    """CSV-aware pipeline entry — returns full AgentState dict."""
    from src.graph.agent import agentic_ai

    run_id = str(initial.get("run_id") or "unknown")
    question = str(initial.get("question") or "")[:120]

    with create_db_session() as session:
        row = RunRow(
            id=run_id,
            question=question,
            datasource_id=initial.get("datasource_id"),
            status="running",
        )
        session.add(row)
        session.flush()

    with log_span(log, "agent_run", run_id=run_id, question=question) as span:
        try:
            final = agentic_ai.invoke(initial)
            status = "completed" if not final.get("error") else "failed"
        except Exception as exc:  # noqa: BLE001
            final = {"error": str(exc), "status": "failed"}
            status = "failed"
        span["status"] = status
        # Copy run_id back so the API can fetch it
        if not final.get("run_id"):
            final["run_id"] = run_id

    with create_db_session() as session:
        row = session.get(RunRow, run_id)
        if row is not None:
            row.status = final.get("status", status)
            row.output_text = final.get("answer")
            row.generated_sql = final.get("code_display") or final.get("sql")
            row.result_row_count = (final.get("sql_result") or {}).get("row_count")
            row.completed_at = datetime.now(timezone.utc)
            row.error_message = final.get("error")

    return final
