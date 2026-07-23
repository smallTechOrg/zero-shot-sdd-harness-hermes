from src.graph.agent import agentic_ai
from src.graph.edges import after_parse, after_execute


def test_graph_compiles_without_env():
    # compiled at import; nodes present
    assert agentic_ai is not None
    node_names = set(agentic_ai.get_graph().nodes)
    assert {"parse_intent", "execute_pandas", "synthesize_dashboard", "handle_error", "finalize"} <= node_names


def test_error_edge_routes_to_handler():
    assert after_parse({"error": "boom"}) == "handle_error"
    assert after_parse({"error": None}) == "execute_pandas"
    assert after_execute({"error": "boom"}) == "handle_error"
    assert after_execute({"error": None}) == "synthesize_dashboard"


def test_parse_intent_node_surfaces_missing_key_as_error(no_keys):
    """With no key, the node returns an actionable error — it never raises."""
    from src.graph.nodes import parse_intent

    out = parse_intent({"user_query": "hi", "csv_schemas": {}})
    assert out["error"] is not None
    assert "AGENT_" in out["error"]  # actionable: names the env vars to set
