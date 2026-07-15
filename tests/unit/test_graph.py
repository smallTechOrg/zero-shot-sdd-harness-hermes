from analytics_agent.graph.agent import analytics_graph
from analytics_agent.graph.state import PipelineState


def test_graph_compiles():
    assert analytics_graph is not None


def test_pipeline_state_shape():
    state: PipelineState = {"entity": "#local", "run_id": "x", "error": None}
    assert state["entity"] == "#local"
