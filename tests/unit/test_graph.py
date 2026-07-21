from src.graph.agent import agentic_ai
from src.graph.edges import after_plan, after_evaluate


def test_graph_compiles_without_env():
    assert agentic_ai is not None
    node_names = set(agentic_ai.get_graph().nodes)
    assert {"plan", "generate_sql", "execute", "evaluate", "finalize", "handle_error"} <= node_names


def test_error_edges_route_to_handler():
    assert after_plan({"error": "boom"}) == "handle_error"
    assert after_plan({"error": None}) == "generate_sql"
    assert after_evaluate({"error": "boom"}) == "handle_error"


def test_plan_node_returns_plan(no_keys):
    from src.graph.nodes import node_plan

    out = node_plan({"question": "q", "datasource_id": "ds", "iteration": 0, "max_iterations": 3})
    assert out.get("plan")
    assert out.get("error") is None
