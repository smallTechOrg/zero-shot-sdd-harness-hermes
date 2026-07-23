"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

import operator
from typing import TypedDict, Any, Annotated

class AgentState(TypedDict, total=False):
    run_id: str
    session_id: str
    user_query: str
    chat_history: Annotated[list[dict[str, Any]], operator.add]
    csv_schemas: dict[str, list[str]]
    temp_paths: dict[str, str]
    intermediate_results: dict[str, Any]
    final_response: dict[str, Any]
    provider: str
    model: str
    status: str
    error: str | None
