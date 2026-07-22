"""Conditional routing functions for the fraud detection analyst graph."""
from __future__ import annotations

from src.graph.state import AgentState


def after_plan_query(state: AgentState) -> str:
 if state.get("error"):
  return "handle_failure"
 return "generate_code"


def after_generate_code(state: AgentState) -> str:
 if state.get("error"):
  return "handle_failure"
 return "execute_query"


def after_execute_query(state: AgentState) -> str:
 if state.get("error"):
  return "handle_failure"
 return "assemble_answer"


def after_assemble_answer(state: AgentState) -> str:
 if state.get("error"):
  return "handle_failure"
 return "finalize"
