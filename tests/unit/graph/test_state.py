"""State TypedDict tests — confirm keys are optional but typed where present."""

from __future__ import annotations

from cctns_analyst.graph.state import AgentState


def test_state_can_be_empty():
    s: AgentState = {}
    assert s == {}


def test_state_optional_keys_round_trip():
    s: AgentState = {
        "request_id": "r",
        "question": "q",
        "sql": "SELECT 1 FROM cctns_mirror.fir",
        "sql_attempts": 1,
        "validation_error": None,
        "columns": ["a"],
        "rows": [(1,)],
        "row_count": 1,
        "answer": "ok",
        "status": "completed",
        "error": None,
        "latency_ms": 100,
    }
    assert s["answer"] == "ok"
    assert s["rows"] == [(1,)]
