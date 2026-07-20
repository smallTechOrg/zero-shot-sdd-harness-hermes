"""CSV Analyst graph assembly."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.capabilities import csv_state
from src.capabilities.csv_nodes import csv_error, csv_explain, csv_execute, csv_finalize, csv_plan, csv_query


def build_agent():
    graph = StateGraph(csv_state.CsvAgentState)

    graph.add_node("csv_plan", csv_plan)
    graph.add_node("csv_query", csv_query)
    graph.add_node("csv_execute", csv_execute)
    graph.add_node("csv_explain", csv_explain)
    graph.add_node("csv_finalize", csv_finalize)
    graph.add_node("csv_error", csv_error)

    graph.set_entry_point("csv_plan")
    graph.add_edge("csv_plan", "csv_query")
    graph.add_edge("csv_execute", "csv_explain")
    graph.add_edge("csv_explain", "csv_finalize")
    graph.add_edge("csv_finalize", END)
    graph.add_edge("csv_error", END)

    def route_after_query(state):
        if state.get("error"):
            return "csv_error"
        return "csv_execute"

    graph.add_conditional_edges(
        "csv_query",
        route_after_query,
        {
            "csv_error": "csv_error",
            "csv_execute": "csv_execute",
        }
    )
    return graph.compile()


agentic_ai = build_agent()