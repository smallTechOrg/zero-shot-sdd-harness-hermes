"""AgentState — extended for the CSV analyst capability."""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: int
    session_id: str | None

    # Input
    question: str
    data_source: str  # "cache" or "live"

    # Schema + plan
    schema_markdown: str | None
    sql: str | None
    chart_spec: dict | None
    suggestions: list[str] | None

    # Tool output
    query_result: dict | None
    tool_error: str | None

    # Final
    output_text: str | None

    # Meta
    provider: str | None
    model: str | None
    latency_ms: int | None
    status: str | None
    error: str | None
