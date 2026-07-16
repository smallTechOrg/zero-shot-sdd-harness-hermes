"""FastAPI dependencies — graph instance wiring."""

from __future__ import annotations

from typing import Any

from cctns_analyst.config.settings import get_settings
from cctns_analyst.graph.runner import _build_bound_graph
from cctns_analyst.llm.client import get_default_llm_client
from cctns_analyst.tools.cctns_mirror import get_mirror_runner


def build_request_graph() -> Any:
    """Build a LangGraph compiled graph with all dependencies bound."""
    settings = get_settings()
    llm = get_default_llm_client()
    runner, schema_provider = get_mirror_runner(settings)
    return _build_bound_graph(
        llm=llm,
        mirror_runner=runner,
        schema_provider=schema_provider,
        row_cap=settings.row_cap,
    )
