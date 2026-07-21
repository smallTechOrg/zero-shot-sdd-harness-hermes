"""run_agent() — the entry point the API calls."""
from __future__ import annotations

from src.db.models import RunRow
from src.db.session import create_db_session
from src.graph.agent import agentic_ai
from src.graph.state import AgentState
from src.observability.events import get_logger, log_span


def run_agent(input_text: str, instruction: str, *, file_count: int = 0) -> str:
    log = get_logger("runner")

    with create_db_session() as session:
        run = RunRow(
            input_text=input_text,
            instruction=instruction,
            status="running",
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AgentState = {
        "run_id": run_id,
        "input_text": input_text,
        "instruction": instruction,
        "error": None,
        "file_count": file_count,
    }
    with log_span(log, "agent_run", run_id=run_id) as span:
        final: AgentState = agentic_ai.invoke(initial)
        span["status"] = final.get("status", "completed")

    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        run.status = final.get("status", "completed")
        run.output_text = final.get("output_text")
        run.provider = final.get("provider")
        run.model = final.get("model")
        run.error_message = final.get("error")

    return run_id
