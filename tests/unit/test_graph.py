from src.graph.agent import agentic_ai
from src.graph.edges import after_execute_tool, after_plan_query


def test_graph_compiles_without_env():
    # compiled at import; nodes present
    assert agentic_ai is not None
    node_names = set(agentic_ai.get_graph().nodes)
    assert {"plan_query", "execute_tool", "finalize", "handle_error"} <= node_names


def test_error_edge_from_plan_query():
    assert after_plan_query({"error": "boom"}) == "handle_error"
    assert after_plan_query({"error": None}) == "execute_tool"


def test_error_edge_from_execute_tool():
    assert after_execute_tool({"tool_error": "boom"}) == "handle_error"
    assert after_execute_tool({"tool_error": None}) == "finalize"


def test_plan_node_surfaces_missing_key_as_error(no_keys):
    from src.graph.nodes import plan_query
    out = plan_query({"session_id": "", "question": "hi", "data_source": "cache"})
    assert out["error"]
    assert "AGENT_" in out["error"]
