"""Agent state — shared dict keys for the baseline graph."""
from __future__ import annotations

from typing import Any, Dict, TypedDict

# Use a TypedDict so LangGraph can type-check node returns.


class AgentState(TypedDict, total=False):
    run_id: str
    session_id: str | None
    input_text: str
    instruction: str
    output_text: str | None
    provider: str | None
    model: str | None
    plan_text: str | None
    generated_code: str | None
    code_language: str | None
    rows: list[Any]
    row_count: int | None
    latency_ms: float | None
    nl_answer: str | None
    chart_spec: dict | None
    kpis: list[Any] | None
    result_hash: str | None
    source: str | None
    cache_hit: bool | None
    clarify_prompt: str | None
    error: str | None
    status: str
