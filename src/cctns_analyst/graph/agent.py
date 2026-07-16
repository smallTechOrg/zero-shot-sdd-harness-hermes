"""LangGraph compile + entry-point.

Compiled graph is built once at import time. The runner invokes it with an
initial state and returns the final state.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from cctns_analyst.graph.edges import (
    EXECUTE_SQL,
    FINALIZE,
    HANDLE_ERROR,
    NL_TO_SQL,
    SUMMARIZE_ANSWER,
    VALIDATE_RESULT,
    after_execute_sql,
    after_nl_to_sql,
    after_summarize,
    after_validate,
)
from cctns_analyst.graph.nodes import (
    execute_sql,
    finalize,
    handle_error,
    nl_to_sql,
    summarize_answer,
    validate_result,
)
from cctns_analyst.graph.state import AgentState


def _build_graph() -> Any:
    g = StateGraph(AgentState)
    # Nodes are registered here as plain callables. The runner injects their
    # bound dependencies (`llm`, `mirror_runner`, …) by composing partial
    # applications in this module.
    g.add_node(NL_TO_SQL, nl_to_sql)
    g.add_node(EXECUTE_SQL, execute_sql)
    g.add_node(VALIDATE_RESULT, validate_result)
    g.add_node(SUMMARIZE_ANSWER, summarize_answer)
    g.add_node(FINALIZE, finalize)
    g.add_node(HANDLE_ERROR, handle_error)
    g.set_entry_point(NL_TO_SQL)
    g.add_conditional_edges(
        NL_TO_SQL,
        after_nl_to_sql,
        {EXECUTE_SQL: EXECUTE_SQL, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        EXECUTE_SQL,
        after_execute_sql,
        {VALIDATE_RESULT: VALIDATE_RESULT, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        VALIDATE_RESULT,
        after_validate,
        {NL_TO_SQL: NL_TO_SQL, SUMMARIZE_ANSWER: SUMMARIZE_ANSWER},
    )
    g.add_conditional_edges(
        SUMMARIZE_ANSWER,
        after_summarize,
        {FINALIZE: FINALIZE, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_edge(FINALIZE, END)
    g.add_edge(HANDLE_ERROR, END)
    return g.compile()


def make_initial_state(question: str, *, request_id: str) -> AgentState:
    """Build the initial AgentState dict for one request."""
    return {
        "request_id": request_id,
        "question": question,
        "sql": None,
        "sql_attempts": 0,
        "validation_error": None,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "answer": None,
        "status": "pending",
        "error": None,
        "latency_ms": 0,
    }


# Module-level compiled graph — built lazily so import-time failures surface
# with a clear stack rather than at first request.
_graph: Any | None = None


def get_compiled_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph
