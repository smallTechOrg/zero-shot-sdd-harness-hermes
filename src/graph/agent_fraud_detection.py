"""Graph assembly — StateGraph compiled once at import for fraud detection."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.edges_fraud_detection import after_execute_query, after_generate_code, after_plan_query
from src.graph.nodes_fraud_detection import assemble_answer, execute_query, finalize, generate_code, handle_failure, plan_query
from src.graph.state import AgentState


AGENT_STATE_NEXT = "next"


def build_fraud_detection_graph():
 g = StateGraph(AgentState)
 g.add_node("plan_query", plan_query)
 g.add_node("generate_code", generate_code)
 g.add_node("execute_query", execute_query)
 g.add_node("assemble_answer", assemble_answer)
 g.add_node("finalize", finalize)
 g.add_node("handle_failure", handle_failure)

 g.set_entry_point("plan_query")
 g.add_conditional_edges("plan_query", after_plan_query, {"generate_code": "generate_code", "handle_failure": "handle_failure"})
 g.add_conditional_edges("generate_code", after_generate_code, {"execute_query": "execute_query", "handle_failure": "handle_failure"})
 g.add_conditional_edges("execute_query", after_execute_query, {"assemble_answer": "assemble_answer", "handle_failure": "handle_failure"})
 g.add_conditional_edges("assemble_answer", after_assemble_answer, {"finalize": "finalize", "handle_failure": "handle_failure"})
 g.add_edge("finalize", END)
 g.add_edge("handle_failure", END)
 return g.compile()
