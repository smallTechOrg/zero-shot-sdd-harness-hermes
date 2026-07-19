"""Graph runtime — wires dependencies into nodes, runs the compiled graph."""

from __future__ import annotations

import time
import uuid
from functools import partial
from typing import Any

from mssql_analyst.config.settings import get_settings
from mssql_analyst.graph.agent import make_initial_state
from mssql_analyst.graph.edges import (
    EXECUTE_SQL,
    FINALIZE,
    HANDLE_ERROR,
    NL_TO_SQL,
    after_execute_sql,
    after_nl_to_sql,
)
from mssql_analyst.graph.state import AgentState
from mssql_analyst.llm.client import LLMClient


def build_request_graph(
    *, llm: LLMClient, nl_to_sql_node, execute_sql_node, finalize_node, handle_error_node
) -> Any:
    """Assemble a LangGraph graph with the four bound nodes."""
    from langgraph.graph import END, StateGraph

    g = StateGraph(AgentState)
    g.add_node(NL_TO_SQL, nl_to_sql_node)
    g.add_node(EXECUTE_SQL, execute_sql_node)
    g.add_node(FINALIZE, finalize_node)
    g.add_node(HANDLE_ERROR, handle_error_node)
    g.set_entry_point(NL_TO_SQL)
    g.add_conditional_edges(
        NL_TO_SQL, after_nl_to_sql,
        {EXECUTE_SQL: EXECUTE_SQL, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_conditional_edges(
        EXECUTE_SQL, after_execute_sql,
        {FINALIZE: FINALIZE, HANDLE_ERROR: HANDLE_ERROR},
    )
    g.add_edge(FINALIZE, END)
    g.add_edge(HANDLE_ERROR, END)
    return g.compile()


def run_agent(question: str, *, request_id: str | None = None) -> dict[str, Any]:
    """Single-request entry point. Returns the flattened final state."""
    from mssql_analyst.graph.nodes import build_nodes
    from mssql_analyst.llm.client import get_default_llm_client
    from mssql_analyst.tools.mssql import get_mssql_connector

    settings = get_settings()
    request_id = request_id or str(uuid.uuid4())
    llm = get_default_llm_client()
    connector = get_mssql_connector()

    def schema_provider():
        return connector.describe_schema()

    nodes = build_nodes(llm=llm, connector=connector, schema_provider=schema_provider)
    graph = build_request_graph(
        llm=llm,
        nl_to_sql_node=nodes["nl_to_sql"],
        execute_sql_node=nodes["execute_sql"],
        finalize_node=nodes["finalize"],
        handle_error_node=nodes["handle_error"],
    )

    initial = make_initial_state(question, request_id=request_id)
    t0 = time.perf_counter()
    final = graph.invoke(initial)
    final["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    if not final.get("status") or final["status"] == "pending":
        final["status"] = "completed" if not final.get("error") else "failed"
    return final
