"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    input_text: str
    instruction: str
    output_text: str
    provider: str
    model: str
    status: str
    error: str | None
    file_count: int
