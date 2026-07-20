"""CSV Analyst tasks."""
from __future__ import annotations

from src.capabilities.agent import agentic_ai
from src.capabilities.csv_state import CsvAgentState
from src.services.sessions import get_session_row


def run_csv_agent(session_id, input_text):
    # Fetch the session to get the schema_summary
    session = get_session_row(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")
    state: CsvAgentState = {
        "session_id": session_id,
        "input_text": input_text,
        "schema_summary": session.schema_summary,
        "conversation_history": [],
    }
    result = agentic_ai.invoke(state)
    return result