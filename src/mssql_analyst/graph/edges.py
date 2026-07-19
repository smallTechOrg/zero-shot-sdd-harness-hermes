"""Conditional edges for the MSSQL analyst state machine (Phase 3).

Phase 3 introduces the ``validate_sql`` node plus a conditional cycle
back to ``nl_to_sql`` (when the validator rejects AND we still have
retry budget). Route names are exported as module-level constants.
"""

from __future__ import annotations

from mssql_analyst.graph.state import AgentState

# Node names — kept in one place so graph/edges.py and graph/agent.py agree.
NL_TO_SQL = "nl_to_sql"
VALIDATE_SQL = "validate_sql"
EXECUTE_SQL = "execute_sql"
FINALIZE = "finalize"
HANDLE_ERROR = "handle_error"

NODES = frozenset(
    {
        NL_TO_SQL,
        VALIDATE_SQL,
        EXECUTE_SQL,
        FINALIZE,
        HANDLE_ERROR,
    }
)


def after_nl_to_sql(state: AgentState) -> str:
    """Route after ``nl_to_sql`` has run.

    - ``error`` set, or empty ``sql`` (LLM could not produce one) ⇒ handle_error.
    - Otherwise forward to the validator.
    """
    if state.get("error") is not None or not (state.get("sql") or "").strip():
        return HANDLE_ERROR
    return VALIDATE_SQL


def after_validate(state: AgentState) -> str:
    """Route after ``validate_sql`` has run.

    - Clean validation ⇒ execute_sql.
    - Validator-rejected but within attempts cap ⇒ cycle back to
      ``nl_to_sql`` with the complaints baked into the prompt context.
    - Validator-rejected and attempts exhausted ⇒ handle_error with the
      last complaint echoed as the public error.
    """
    attempts = int(state.get("sql_attempts") or 0)
    max_attempts = int(state.get("max_sql_attempts") or 2)
    if not state.get("validation_retry_pending"):
        # Clean — proceed to execute.
        return EXECUTE_SQL
    # A retry is pending.
    if attempts < max_attempts:
        return NL_TO_SQL
    # Budget exhausted — surface the last complaint as the public error.
    complaints = state.get("validation_complaints") or []
    last = complaints[-1] if complaints else "validation_failed"
    return HANDLE_ERROR if state.get("set_validation_error") is None else HANDLE_ERROR


def after_execute_sql(state: AgentState) -> str:
    """After the executor ran, finalize or error."""
    if state.get("error") is not None:
        return HANDLE_ERROR
    return FINALIZE
