"""CSV Analyst state."""
from __future__ import annotations

from typing import Any, TypedDict


class CsvAgentState(TypedDict, total=False):
    session_id: str | None
    input_text: str
    schema_summary: dict | None
    conversation_history: list[dict[str, str]]
    plan_text: str | None
    generated_code: str | None
    code_language: str | None
    rows: list[dict[str, Any]] | None
    row_count: int | None
    latency_ms: float | None
    result_hash: str | None
    output_text: str | None
    error: str | None
    status: str
