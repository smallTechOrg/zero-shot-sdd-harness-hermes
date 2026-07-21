"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Identity
    run_id: str
    user_id: str

    # Input
    question: str
    datasource_id: str | None
    uploaded_files: list[str] | None

    # Pipeline data (populated progressively by nodes)
    plan: list[str] | None
    sql: str | None
    sql_result: dict[str, Any] | None
    evaluate_score: float | None
    iteration: int
    max_iterations: int

    # Output
    answer: str | None
    code_display: str | None
    chart_urls: list[str] | None
    download_urls: list[dict[str, str]] | None

    # Control
    error: str | None
    checkpoint: str | None
