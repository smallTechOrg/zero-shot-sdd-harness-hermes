"""LangGraph compile + entry-point.

Compiled graph is built lazily on first use so import-time failures surface
with a clear stack rather than at first request.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from mssql_analyst.graph.edges import (
    EXECUTE_SQL,
    FINALIZE,
    HANDLE_ERROR,
    NL_TO_SQL,
    after_execute_sql,
    after_nl_to_sql,
)
from mssql_analyst.graph.state import AgentState


def _build_unbound_graph() -> Any:
    """Build the graph with node symbols; real bindings happen in the runner.

    This shape is used only for the unit test that asserts graph topology
    compiles (no real LLM/MSSQL needed). Phase-3 adds ``validate_sql``
    and the cycle back to ``nl_to_sql``.
    """
    from mssql_analyst.graph.nodes import (
        execute_sql,
        finalize,
        handle_error,
        nl_to_sql,
        validate_sql,
    )
    from mssql_analyst.graph.edges import VALIDATE_SQL, after_validate

    g = StateGraph(AgentState)
    g.add_node(NL_TO_SQL, nl_to_sql)
    g.add_node(VALIDATE_SQL, validate_sql)
    g.add_node(EXECUTE_SQL, execute_sql)
    g.add_node(FINALIZE, finalize)
    g.add_node(HANDLE_ERROR, handle_error)
    g.set_entry_point(NL_TO_SQL)
    g.add_conditional_edges(
        NL_TO_SQL, after_nl_to_sql,
        {VALIDATE_SQL: VALIDATE_SQL, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        VALIDATE_SQL, after_validate,
        {
            EXECUTE_SQL: EXECUTE_SQL,
            NL_TO_SQL: NL_TO_SQL,
            HANDLE_ERROR: HANDLE_ERROR,
        },
    )
    g.add_conditional_edges(
        EXECUTE_SQL, after_execute_sql,
        {FINALIZE: FINALIZE, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_edge(FINALIZE, END)
    g.add_edge(HANDLE_ERROR, END)
    return g.compile()


_graph: Any | None = None


def get_compiled_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = _build_unbound_graph()
    return _graph


def make_initial_state(question: str, *, request_id: str) -> AgentState:
    """Build the initial AgentState dict for one request."""
    return {
        "request_id": request_id,
        "question": question,
        "max_sql_attempts": 2,  # Phase-3 default
        "sql": None,
        "sql_attempts": 0,
        "validation_error": None,
        "validation_complaints": [],
        "validation_retry_pending": False,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "tokens_used": 0,
        "row_cap_effective": 0,
        "status": "pending",
        "error": None,
        "latency_ms": 0,
        "timelines": [],
    }
