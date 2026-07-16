"""Graph runtime — wires dependencies into nodes, runs the compiled graph."""

from __future__ import annotations

import time
import uuid
from functools import partial
from typing import Any

from cctns_analyst.config.settings import get_settings
from cctns_analyst.graph.agent import (
    get_compiled_graph,
    make_initial_state,
)
from cctns_analyst.graph.edges import (
    EXECUTE_SQL,
    FINALIZE,
    HANDLE_ERROR,
    NL_TO_SQL,
    SUMMARIZE_ANSWER,
    VALIDATE_RESULT,
)
from cctns_analyst.graph.nodes import (
    execute_sql,
    handle_error,
    nl_to_sql,
    summarize_answer,
    validate_result,
)
from cctns_analyst.llm.client import LLMClient, get_default_llm_client
from cctns_analyst.tools.cctns_mirror import get_mirror_runner


def _build_bound_graph(
    *, llm: LLMClient, mirror_runner, schema_provider, row_cap: int
) -> Any:
    """Compile the graph with bound dependencies for each node.

    LangGraph calls a node with one argument (the state). We bind the
    keyword-only arguments via :func:`functools.partial` so each node only
    sees the state.
    """
    from langgraph.graph import END, StateGraph

    from cctns_analyst.graph.edges import (
        after_execute_sql,
        after_nl_to_sql,
        after_summarize,
        after_validate,
    )
    from cctns_analyst.graph.state import AgentState

    g = StateGraph(AgentState)
    g.add_node(NL_TO_SQL, partial(nl_to_sql, llm=llm, schema_provider=schema_provider))
    g.add_node(EXECUTE_SQL, partial(execute_sql, mirror_runner=mirror_runner, row_cap=row_cap))
    g.add_node(VALIDATE_RESULT, validate_result)
    g.add_node(SUMMARIZE_ANSWER, partial(summarize_answer, llm=llm))
    g.add_node(FINALIZE, lambda state: {"status": "completed"}
               if state.get("status") != "failed"
               else {"status": "failed"})
    g.add_node(HANDLE_ERROR, lambda state: {"status": "failed",
                                            "error": state.get("error") or "unknown_failure"})
    g.set_entry_point(NL_TO_SQL)
    g.add_conditional_edges(
        NL_TO_SQL, after_nl_to_sql,
        {EXECUTE_SQL: EXECUTE_SQL, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        EXECUTE_SQL, after_execute_sql,
        {VALIDATE_RESULT: VALIDATE_RESULT, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        VALIDATE_RESULT, after_validate,
        {NL_TO_SQL: NL_TO_SQL, SUMMARIZE_ANSWER: SUMMARIZE_ANSWER},
    )
    g.add_conditional_edges(
        SUMMARIZE_ANSWER, after_summarize,
        {FINALIZE: FINALIZE, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_edge(FINALIZE, END)
    g.add_edge(HANDLE_ERROR, END)
    return g.compile()


def run_agent(question: str, *, request_id: str | None = None) -> dict[str, Any]:
    """Single-request entry point. Returns the flattened final state."""
    settings = get_settings()
    request_id = request_id or str(uuid.uuid4())
    llm = get_default_llm_client()
    mirror_runner, schema_provider = get_mirror_runner()

    graph = _build_bound_graph(
        llm=llm,
        mirror_runner=mirror_runner,
        schema_provider=schema_provider,
        row_cap=settings.row_cap,
    )

    initial = make_initial_state(question, request_id=request_id)
    t0 = time.perf_counter()
    final = graph.invoke(initial)
    final["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    # Make sure `status` is set
    if not final.get("status") or final["status"] == "pending":
        final["status"] = "completed" if not final.get("error") else "failed"
    return final


def get_unbound_compiled_graph() -> Any:
    """Legacy entry — exposed for the unit graph test that doesn't bind deps."""
    return get_compiled_graph()
