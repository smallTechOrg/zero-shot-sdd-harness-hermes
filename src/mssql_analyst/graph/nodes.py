"""LangGraph nodes for the MSSQL analyst agent.

Each node is a function ``(state) -> partial state`` that returns only the
keys it sets or mutates. The graph runner merges them.

LLM nodes call into ``mssql_analyst.llm.client.LLMClient``; they never call
provider SDKs directly. The MSSQL node calls into the connector so the
executor can be swapped (Phase 2 mock-for-tests if needed) without touching
the graph.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from mssql_analyst.graph.state import AgentState
from mssql_analyst.llm.client import LLMClient, get_default_llm_client
from mssql_analyst.observability.events import get_logger
from mssql_analyst.prompts.loader import load_prompt
from mssql_analyst.tools.mssql import MssqlConnector, get_mssql_connector
from mssql_analyst.tools.validator import UnsafeSQLError, assert_select_only

logger = get_logger("mssql_analyst.graph.nodes")


# ---------------------------------------------------------------------------
# Factory: build node-bound callables for the graph runner
# ---------------------------------------------------------------------------


def build_nodes(
    *,
    llm: LLMClient,
    connector: MssqlConnector,
    schema_provider: Callable[[], dict[str, list[dict[str, str]]]],
) -> dict[str, Callable[[AgentState], AgentState]]:
    """Return a dict of {node_name: callable} ready for the runner.

    Keeping the wiring here lets the runner stay tiny, and lets tests
    swap ``llm`` / ``connector`` directly with no monkey-patching.
    """

    def nl_to_sql(state: AgentState) -> AgentState:
        q = (state.get("question") or "").strip()
        if not q:
            return {"error": "empty_question", "status": "failed"}
        try:
            schema = schema_provider()
            template = load_prompt("nl_to_sql")
            payload = {"schema": schema, "question": q}
            res = llm.call_json(
                prompt_name="nl_to_sql",
                template=template,
                user_payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            return _capture(state, exc, where="nl_to_sql")

        sql = _extract_sql(res.content)
        attempts = int(state.get("sql_attempts") or 0) + 1
        tokens = int(state.get("tokens_used") or 0) + int(res.total_tokens or 0)

        if not sql:
            return {
                "sql": None,
                "sql_attempts": attempts,
                "tokens_used": tokens,
                "error": "llm_returned_empty_sql",
                "status": "failed",
            }
        try:
            assert_select_only(sql)
        except UnsafeSQLError as exc:
            return {
                "sql": sql,
                "sql_attempts": attempts,
                "tokens_used": tokens,
                "validation_error": str(exc),
                "error": f"unsafe_sql: {exc}",
                "status": "failed",
            }
        return {
            "sql": sql,
            "sql_attempts": attempts,
            "tokens_used": tokens,
            "validation_error": None,
        }

    def execute_sql(state: AgentState) -> AgentState:
        sql = state.get("sql") or ""
        if not sql:
            return {"error": "no_sql", "status": "failed"}
        try:
            t0 = time.perf_counter()
            columns, rows, raw_count = connector.execute(sql)
            latency_ms = int(state.get("latency_ms") or 0) + int(
                (time.perf_counter() - t0) * 1000
            )
        except Exception as exc:  # noqa: BLE001
            return _capture(state, exc, where="execute_sql")
        return {
            "columns": list(columns),
            "rows": [tuple(r) for r in rows],
            "row_count": int(raw_count),
            "latency_ms": latency_ms,
        }

    def finalize(state: AgentState) -> AgentState:
        if state.get("status") == "failed":
            return {"status": "failed"}
        return {"status": "completed"}

    def handle_error(state: AgentState) -> AgentState:
        return {
            "status": "failed",
            "error": state.get("error") or "unknown_failure",
        }

    return {
        "nl_to_sql": nl_to_sql,
        "execute_sql": execute_sql,
        "finalize": finalize,
        "handle_error": handle_error,
    }


# ---------------------------------------------------------------------------
# Plain (unbound) node symbols — used by the unit graph test only.
# ---------------------------------------------------------------------------


def _nl_to_sql_unbound(state: AgentState) -> AgentState:
    """Used only so the unit graph test compiles. The runner never calls me."""
    return {**state, "validation_error": None}


def _execute_sql_unbound(state: AgentState) -> AgentState:
    return {**state, "row_count": 0}


def _finalize_unbound(state: AgentState) -> AgentState:
    return {**state, "status": "completed" if not state.get("error") else "failed"}


def _handle_error_unbound(state: AgentState) -> AgentState:
    return {**state, "status": "failed"}


# Aliases for the runner — these are the bound callables injected per request.
gather_bound_nodes = build_nodes  # exported for the runner

# Re-bindable globals injected into the agent by the runner.
llm_singleton = None
connector_singleton = None


def get_default_nodes() -> dict[str, Callable[[AgentState], AgentState]]:
    """Resolve nodes with the process-defaults LLM and MSSQL connector."""
    if llm_singleton is None:
        bound_llm = get_default_llm_client()
    else:
        bound_llm = llm_singleton
    if connector_singleton is None:
        bound_connector = get_mssql_connector()
    else:
        bound_connector = connector_singleton

    def schema_provider() -> dict[str, list[dict[str, str]]]:
        return bound_connector.describe_schema()

    return build_nodes(
        llm=bound_llm,
        connector=bound_connector,
        schema_provider=schema_provider,
    )


# Aliases for the unbound nodes (unit graph test only).
nl_to_sql = _nl_to_sql_unbound
execute_sql = _execute_sql_unbound
finalize = _finalize_unbound
handle_error = _handle_error_unbound


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_sql(content: Any) -> str:
    """Get ``"sql"`` out of an LLM response, tolerant of shapes."""
    if isinstance(content, dict):
        sql = content.get("sql") or content.get("SQL") or ""
        return str(sql).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _capture(state: AgentState, exc: Exception, *, where: str) -> dict[str, Any]:
    """Capture an exception onto the state without ever raising again."""
    logger.warning("graph_node_failed", extra={"where": where, "exc": repr(exc)})
    return {
        "error": _public_message(exc),
        "status": "failed",
    }


def _public_message(exc: Exception) -> str:
    """Build a public message that does NOT leak repr(exc) (a stack trace)."""
    msg = str(exc).strip()
    if not msg:
        msg = exc.__class__.__name__
    return msg[:300]


def _serialise_row(r: tuple) -> list:
    """JSON-safe row serializer — datetime etc. -> python primitives."""
    out = []
    for v in r:
        if v is None:
            out.append(None)
            continue
        if hasattr(v, "isoformat"):
            try:
                out.append(v.isoformat())
                continue
            except Exception:  # noqa: BLE001
                pass
        if hasattr(v, "item"):
            try:
                out.append(v.item())
                continue
            except Exception:  # noqa: BLE001
                pass
        out.append(v)
    return out
