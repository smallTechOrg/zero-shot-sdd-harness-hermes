"""Conditional routing functions."""

from __future__ import annotations

from src.graph.state import AgentState


def after_plan_query(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "execute_tool"


def after_execute_tool(state: AgentState) -> str:
    return "handle_error" if state.get("tool_error") else "finalize"
