from langgraph.graph import END, StateGraph

from analytics_agent.graph.edges import (
    after_aggregate,
    after_compute,
    after_fetch,
)
from analytics_agent.graph.nodes import (
    aggregate_node,
    compute_funnel,
    fetch_sources,
    finalize,
    handle_error,
    narrate,
)
from analytics_agent.graph.state import PipelineState


def _build_graph() -> StateGraph:
    g = StateGraph(PipelineState)
    g.add_node("fetch_sources", fetch_sources)
    g.add_node("aggregate", aggregate_node)
    g.add_node("compute_funnel", compute_funnel)
    g.add_node("narrate", narrate)
    g.add_node("handle_error", handle_error)
    g.add_node("finalize", finalize)

    g.set_entry_point("fetch_sources")
    g.add_conditional_edges(
        "fetch_sources", after_fetch, {"aggregate": "aggregate", "handle_error": "handle_error"}
    )
    g.add_conditional_edges(
        "aggregate",
        after_aggregate,
        {"compute_funnel": "compute_funnel", "handle_error": "handle_error"},
    )
    g.add_conditional_edges(
        "compute_funnel",
        after_compute,
        {"narrate": "narrate", "handle_error": "handle_error"},
    )
    g.add_edge("narrate", "finalize")
    g.add_edge("handle_error", END)
    g.add_edge("finalize", END)
    return g.compile()


analytics_graph = _build_graph()
