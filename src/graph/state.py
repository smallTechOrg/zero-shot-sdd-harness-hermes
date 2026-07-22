"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

from typing import TypedDict, Any

class AgentState(TypedDict, total=False):
    run_id: str
    session_id: str
    user_query: str
    csv_schemas: dict[str, list[str]]
    temp_paths: dict[str, str]
    intermediate_results: dict[str, Any]
    final_response: dict[str, Any]
    provider: str
    model: str
    status: str
    error: str | None
