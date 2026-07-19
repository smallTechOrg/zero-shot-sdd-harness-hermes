"""Smoke test — graph topology compiles without env / network."""

from __future__ import annotations


def test_graph_compiles_no_env():
    """The unbound graph should compile with no env / network."""
    from mssql_analyst.graph.agent import get_compiled_graph

    g = get_compiled_graph()
    assert g is not None


def test_initial_state_minimal():
    from mssql_analyst.graph.agent import make_initial_state

    s = make_initial_state("How many tables are in master?", request_id="r1")
    assert s["question"] == "How many tables are in master?"
    assert s["status"] == "pending"
    assert s["sql"] is None
    assert s["tokens_used"] == 0
