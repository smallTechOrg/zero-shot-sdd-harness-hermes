"""Graph edges unit tests — deterministic, no LLM."""

from __future__ import annotations

from cctns_analyst.graph.edges import (
    EXECUTE_SQL,
    FINALIZE,
    HANDLE_ERROR,
    NL_TO_SQL,
    SUMMARIZE_ANSWER,
    VALIDATE_RESULT,
    after_execute_sql,
    after_nl_to_sql,
    after_summarize,
    after_validate,
)
from cctns_analyst.graph.state import AgentState


def _state(**kwargs) -> AgentState:
    s: AgentState = {}
    s.update(kwargs)  # type: ignore[typeddict-item]
    return s


def test_after_nl_to_sql_empty_returns_handle_error():
    assert after_nl_to_sql(_state(question="?", sql=None)) == HANDLE_ERROR


def test_after_nl_to_sql_whitespace_sql_returns_handle_error():
    assert after_nl_to_sql(_state(question="?", sql="   ")) == HANDLE_ERROR


def test_after_nl_to_sql_nonempty_returns_execute_sql():
    assert after_nl_to_sql(_state(question="?", sql="SELECT 1 FROM cctns_mirror.fir")) == EXECUTE_SQL


def test_after_execute_sql_error_routes_to_handle_error():
    assert after_execute_sql(_state(error="boom")) == HANDLE_ERROR


def test_after_execute_sql_validation_routing():
    assert after_execute_sql(_state(rows=[], error=None)) == VALIDATE_RESULT


def test_after_validate_retry_under_budget():
    assert after_validate(
        _state(validation_error="bad_sql", sql_attempts=1)
    ) == NL_TO_SQL


def test_after_validate_no_retry_when_budget_exhausted():
    assert after_validate(
        _state(validation_error="bad_sql", sql_attempts=2)
    ) == SUMMARIZE_ANSWER


def test_after_validate_clean_routes_to_summarize():
    assert after_validate(
        _state(validation_error=None, rows=[("a",)], columns=["c"], sql_attempts=1)
    ) == SUMMARIZE_ANSWER


def test_after_summarize_no_answer_goes_handle_error():
    assert after_summarize(_state(answer="")) == HANDLE_ERROR
    assert after_summarize(_state(error="x")) == HANDLE_ERROR


def test_after_summarize_ok_goes_finalize():
    assert after_summarize(_state(answer="There were 17 FIRs.")) == FINALIZE
