"""LangGraph state for the MSSQL analyst agent.

Phase 3 additions for the validator-retry loop:
- ``validation_error``: structural problems found by Phase-3
  ``validate_sql`` (separately from the Phase-1 ``assert_select_only``
  safety gate). Phase-3 routes on this key.
- ``validation_complaints``: list of strings fed into the next
  ``nl_to_sql`` prompt so the LLM retries with feedback.
- ``validation_retry_pending``: True when the validator rejected SQL and
  the graph should route back to ``nl_to_sql`` (until attempts cap).
- ``max_sql_attempts``: set on the initial state; Phase-3 default = 2.
- ``timelines``: list of timing dicts (one per node execution) built
  during the run; the runner persists it to the audit log for the new
  ``/api/runs/{run_id}/timeline`` endpoint.
- ``row_cap_effective``: the cap the executor actually used, after
  Phase-3's token-aware shrink kicked in.
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
    max_sql_attempts: int  # Phase-3 default = 2

    # nl_to_sql outputs
    sql: str | None
    sql_attempts: int
    validation_error: str | None  # populated when the validator rejects
    validation_complaints: list[str]  # Phase-3: list of LLM-hint strings
    validation_retry_pending: bool  # Phase-3: True triggers a cycle back

    # execute_sql outputs
    columns: list[str]
    rows: list[tuple]
    row_count: int
    tokens_used: int
    row_cap_effective: int  # Phase-3: actual cap used by executor

    # terminal
    status: str  # "completed" | "failed"
    error: str | None
    latency_ms: int

    # Phase-3 structured observability — appended-to list of timings.
    # Persisted as JSON to answer_runs.timeline_json; surfaced via the
    # /api/runs/{run_id}/timeline endpoint.
    timelines: list[dict]

    # Phase-3 token-aware cron — set to True so the LLM knows we are in
    # retry mode (use this to alter the system prompt if needed).
    # Currently unused but reserved for future expansion.
    _token_pressure: bool
