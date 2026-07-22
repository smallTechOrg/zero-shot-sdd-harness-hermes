"""Edge functions for routing."""
from __future__ import annotations

from src.graph.state import AgentState


def after_parse(state: AgentState) -> str:
    """Routes after parse_intent."""
    if state.get("error"):
        return "handle_error"
    return "execute_pandas"


def after_execute(state: AgentState) -> str:
    """Routes after execute_pandas."""
    if state.get("error"):
        return "handle_error"
    return "synthesize_dashboard"
