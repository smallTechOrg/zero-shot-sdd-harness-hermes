"""Graph assembly — StateGraph compiled once at import."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.edges import after_evaluate, after_execute, after_plan
from src.graph.nodes import (
    handle_error,
    node_evaluate,
    node_execute,
    node_finalize,
    node_generate_sql,
    node_plan,
)
from src.graph.state import AgentState


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("plan", node_plan)
    g.add_node("generate_sql", node_generate_sql)
    g.add_node("execute", node_execute)
    g.add_node("evaluate", node_evaluate)
    g.add_node("finalize", node_finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("plan")

    g.add_conditional_edges("plan", after_plan, {"generate_sql": "generate_sql", "handle_error": "handle_error"})
    g.add_edge("generate_sql", "execute")
    g.add_conditional_edges("execute", after_execute, {"evaluate": "evaluate", "handle_error": "handle_error"})
    g.add_conditional_edges(
        "evaluate",
        after_evaluate,
        {
            "generate_sql": "generate_sql",
            "finalize": "finalize",
            "handle_error": "handle_error",
        },
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


agentic_ai = _build_graph()
