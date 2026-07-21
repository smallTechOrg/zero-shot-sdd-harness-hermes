"""Graph assembly — StateGraph compiled once at import."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.edges import after_transform
from src.graph.nodes import analyze_data, finalize, handle_error
from src.graph.state import AgentState


def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("analyze_data", analyze_data)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)
    g.set_entry_point("analyze_data")
    g.add_conditional_edges(
        "analyze_data",
        after_transform,
        {"finalize": "finalize", "handle_error": "handle_error"},
    )
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)
    return g.compile()


agentic_ai = _build_graph()
