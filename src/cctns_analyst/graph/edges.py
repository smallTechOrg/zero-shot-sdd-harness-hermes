"""Conditional edges for the CCTNS analyst state machine.

Each function inspects `state` and returns the name of the next node.
Returning a string that is not declared when the edge is added is an
`InvalidTransitionError` from LangGraph — therefore names are kept as
module-level constants.
"""

from __future__ import annotations

from cctns_analyst.graph.state import AgentState

# Node names — kept in one place so ``graph/agent.py`` and ``edges.py`` agree.
NL_TO_SQL = "nl_to_sql"
EXECUTE_SQL = "execute_sql"
VALIDATE_RESULT = "validate_result"
SUMMARIZE_ANSWER = "summarize_answer"
FINALIZE = "finalize"
HANDLE_ERROR = "handle_error"

NODES = frozenset(
    {
        NL_TO_SQL,
        EXECUTE_SQL,
        VALIDATE_RESULT,
        SUMMARIZE_ANSWER,
        FINALIZE,
        HANDLE_ERROR,
    }
)


def after_nl_to_sql(state: AgentState) -> str:
    """Route after the LLM has attempted to draft SQL.

    - Empty SQL ⇒ protocol failure ⇒ handle_error.
    - Otherwise ⇒ execute_sql.
    """
    if state.get("error") is not None or not (state.get("sql") or "").strip():
        return HANDLE_ERROR
    return EXECUTE_SQL


def after_execute_sql(state: AgentState) -> str:
    """Route after the bounded executor has run."""
    if state.get("error") is not None:
        return HANDLE_ERROR
    return VALIDATE_RESULT


def after_validate(state: AgentState) -> str:
    """Route after the validator.

    - Validator returned an error AND we still have retry budget ⇒ go back to
      ``nl_to_sql`` with the validator's complaint in the prompt context.
    - Empty result is allowed (the answer can say "no rows") ⇒ summarize.
    - Otherwise ⇒ summarize.
    """
    if state.get("validation_error") and (state.get("sql_attempts") or 1) < 2:
        return NL_TO_SQL
    return SUMMARIZE_ANSWER


def after_summarize(state: AgentState) -> str:
    """Route after the LLM has summarised the bounded result."""
    if state.get("error") is not None or not (state.get("answer") or "").strip():
        return HANDLE_ERROR
    return FINALIZE
