"""LangGraph state for the MSSQL analyst agent.

Phase 3 additions for the validator-retry loop:
- ``validation_error``: structural problems found by Phase-3
  ``validate_sql`` (separately from the Phase-1 ``assert_select_only``
  safety gate). Phase-3 routes on this key.
- ``timelines``: a list of timing dicts (one per node execution) built
  during the run; the runner persists it to the audit log for the new
  ``/api/runs/{run_id}/timeline`` endpoint.
- ``row_cap_effective``: the cap that the executor actually used, after
  Phase-3's token-aware shrink kicked in (default = ``row_cap``).
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """State threaded through the LangGraph nodes.

    Lives for one request only. Every field is optional; nodes fill what
    they need. The shape is documented in ``spec/agent.md`` and is law for
    the graph.
    """

    # inputs
    request_id: str
    question: str
    max_sql_attempts: int  # Phase-3: set on the initial state (default 2)

    # nl_to_sql outputs
    sql: str | None
    sql_attempts: int
    validation_error: str | None  # populated when the validator rejects

    # execute_sql outputs
    columns: list[str]
    rows: list[tuple]
    row_count: int
    tokens_used: int
    row_cap_effective: int

    # terminal
    status: str  # "completed" | "failed"
    error: str | None
    latency_ms: int

    # Phase-3 structured observability — appended-to list of timings
    # (one entry per node execution). Surfaced via the new
    # /api/runs/{run_id}/timeline endpoint.
    timelines: list[dict]

