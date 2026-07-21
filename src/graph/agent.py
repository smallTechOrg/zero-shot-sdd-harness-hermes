"""Graph assembly — StateGraph compiled once at import."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.edges import after_execute_tool, after_plan_query
from src.graph.nodes import execute_tool, finalize, handle_error, plan_query
from src.graph.state import AgentState


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("plan_query", plan_query)
    g.add_node("execute_tool", execute_tool)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)
    g.set_entry_point("plan_query")
    g.add_conditional_edges(
        "plan_query",
        after_plan_query,
        {"execute_tool": "execute_tool", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "execute_tool",
        after_execute_tool,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
