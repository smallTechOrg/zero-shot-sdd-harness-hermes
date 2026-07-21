from src.graph.agent import agentic_ai
from src.graph.edges import after_transform


def test_graph_compiles_without_env():
    assert agentic_ai is not None
    node_names = set(agentic_ai.get_graph().nodes)
    assert {"analyze_data", "handle_error", "finalize"} <= node_names


def test_error_edge_routes_to_handler():
    assert after_transform({"error": "boom"}) == "handle_error"
    assert after_transform({"error": None}) == "finalize"


def test_analyze_node_surfaces_missing_key_as_error(no_keys):
    out = __import__("src.graph.nodes", fromlist=["analyze_data"]).analyze_data(
        {"input_text": "summary", "instruction": "question"}
    )
    assert out["error"] is not None
    assert "AGENT_" in out["error"]
