"""Conditional edges for the MSSQL analyst state machine."""

from __future__ import annotations

from mssql_analyst.graph.state import AgentState

# Node names — kept in one place so ``graph/agent.py`` and ``edges.py`` agree.
NL_TO_SQL = "nl_to_sql"
EXECUTE_SQL = "execute_sql"
FINALIZE = "finalize"
HANDLE_ERROR = "handle_error"

NODES = frozenset(
    {
        NL_TO_SQL,
        EXECUTE_SQL,
        FINALIZE,
        HANDLE_ERROR,
    }
)


def after_nl_to_sql(state: AgentState) -> str:
    """Route after the LLM has attempted to draft SQL.

    - Empty SQL ⇒ protocol failure ⇒ handle_error.
    - Validator error ⇒ handle_error.
    - Otherwise ⇒ execute_sql.
    """
    if state.get("error") is not None or not (state.get("sql") or "").strip():
        return HANDLE_ERROR
    return EXECUTE_SQL


def after_execute_sql(state: AgentState) -> str:
    """Route after the executor has run."""
    if state.get("error") is not None:
        return HANDLE_ERROR
    return FINALIZE
