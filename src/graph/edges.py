"""Conditional routing functions."""
from __future__ import annotations

from src.graph.state import AgentState


def after_plan(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    return "generate_sql"


def after_execute(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    return "evaluate"


def after_evaluate(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    score = float(state.get("evaluate_score") or 0.0)
    iteration = int(state.get("iteration") or 0)
    max_iterations = int(state.get("max_iterations") or 3)
    if score >= 0.8 or iteration >= max_iterations:
        return "finalize"
    return "generate_sql"


# Backward-compatible shim for the baseline test suite. If stale imports land here,
# route to the original baseline terminal behaviour.
def after_transform(state: AgentState) -> str:
    if state.get("error"):
        return "handle_error"
    return "finalize"
