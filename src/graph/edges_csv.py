"""Conditional routing functions for the CSV analyst graph."""
from __future__ import annotations

from src.graph.state import AgentState


def after_plan_query(state: AgentState) -> str:
 return "handle_error" if state.get("error") else "generate_code"


def after_generate_code(state: AgentState) -> str:
 return "handle_error" if state.get("error") else "execute_query"


def after_execute_query(state: AgentState) -> str:
 # Even on query failure we try to assemble a best-guess answer with the error shown.
 return "assemble_answer"


def after_assemble_answer(state: AgentState) -> str:
 return "handle_error" if state.get("error") else "finalize"
