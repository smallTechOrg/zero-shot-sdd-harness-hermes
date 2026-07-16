"""LangGraph state for the CCTNS analyst agent."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """State threaded through the LangGraph nodes.

    Lives for one request only. Every field is optional; nodes fill what they
    need. The shape is documented in `spec/agent.md` and is law for the
    graph.
    """

    # inputs
    request_id: str
    question: str

    # nl_to_sql outputs
    sql: str | None
    sql_attempts: int
    validation_error: str | None  # populated when the validator rejects

    # execute_sql outputs
    columns: list[str]
    rows: list[tuple]
    row_count: int

    # summarize_answer outputs
    answer: str | None

    # finalize / error terminal nodes
    status: str  # "completed" | "failed"
    error: str | None
    latency_ms: int
