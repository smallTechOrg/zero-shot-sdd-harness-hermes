"""CSV Analyst tasks."""
from __future__ import annotations

from src.capabilities.agent import agentic_ai
from src.capabilities.csv_state import CsvAgentState


def run_csv_agent(session_id, input_text):
    state: CsvAgentState = {
        "session_id": session_id,
        "input_text": input_text,
    }
    result = agentic_ai.invoke(state)
    return result
