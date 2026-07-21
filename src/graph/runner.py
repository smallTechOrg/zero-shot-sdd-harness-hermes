"""run_agent() — entry point the API calls (query_data capability)."""
from __future__ import annotations

import time

from src.db.models import RunRow
from src.db.session import create_db_session
from src.graph.agent import agentic_ai
from src.graph.state import AgentState
from src.observability.events import get_logger, log_span


def run_agent(
    instruction: str,
    session_id: str | None = None,
    data_source: str = "cache",
    uploaded_files: list[str] | None = None,
) -> str:
    log = get_logger("runner")
    t0 = time.perf_counter()

    final_state: AgentState = {
        "status": "failed",
        "error": "graph did not return a final state",
        "provider": None,
        "model": None,
        "output_text": None,
    }

    with create_db_session() as session:
        run = RunRow(
            input_text=instruction,
            instruction=instruction,
            status="running",
        )
        session.add(run)
        session.flush()
        run_id = run.id

        initial: AgentState = {
            "run_id": run_id,
            "instruction": instruction,
            "data_source": data_source,
            "session_id": session_id,
            "uploaded_files": uploaded_files,
            "error": None,
        }
        with log_span(log, "agent_run", run_id=run_id) as span:
            final_state = agentic_ai.invoke(initial)
            span["status"] = final_state.get("status", "completed")

        run.status = final_state.get("status", "completed") or "completed"
        run.output_text = final_state.get("output_text")
        run.provider = final_state.get("provider")
        run.model = final_state.get("model")
        run.error_message = final_state.get("error") or final_state.get("error_message")

        latency_ms = int((time.perf_counter() - t0) * 1000)
        if run.output_text:
            try:
                import json as _json

                envelope = _json.loads(run.output_text)
                envelope["_latency_ms"] = latency_ms
                run.output_text = _json.dumps(envelope)
            except Exception:  # noqa: BLE001
                pass

    return str(run_id)
