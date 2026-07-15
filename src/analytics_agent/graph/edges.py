from analytics_agent.graph.state import PipelineState


def after_fetch(state: PipelineState) -> str:
    if state.get("error"):
        return "handle_error"
    return "aggregate"


def after_aggregate(state: PipelineState) -> str:
    if state.get("error"):
        return "handle_error"
    return "compute_funnel"


def after_compute(state: PipelineState) -> str:
    if state.get("error"):
        return "handle_error"
    return "narrate"
