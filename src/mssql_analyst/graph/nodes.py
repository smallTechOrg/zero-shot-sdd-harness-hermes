"""LangGraph nodes for the MSSQL analyst agent (Phase 3).

The Phase-3 graph is:

```
    [nl_to_sql] ──▶ [validate_sql] ──(clean)──▶ [execute_sql] ─▶ [finalize] ─▶ END
            │              │                       │
            │              │                       └──(error)─▶ [handle_error] ─▶ END
            │              └──(reject, attempts left) ─▶ (back to nl_to_sql)
            │              └──(reject, no budget)     ─▶ [handle_error] ─▶ END
            └──(error)─────────────────────────────────▶ [handle_error] ─▶ END
```

Each node is a function ``(state) -> partial state`` that returns only the
keys it sets or mutates. The graph runner merges them.

LLM nodes call into ``mssql_analyst.llm.client.LLMClient`` — they never
call provider SDKs directly. The MSSQL node calls into the connector so
the executor can be swapped (Phase-2 mock-for-tests if needed) without
touching the graph.

Every node records its own timing dict to ``state["timelines"]`` so the
runner can persist the structured observability surface.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from mssql_analyst.graph.state import AgentState
from mssql_analyst.llm.client import LLMClient
from mssql_analyst.observability.events import get_logger
from mssql_analyst.prompts.loader import load_prompt
from mssql_analyst.tools.mssql import MssqlConnector
from mssql_analyst.tools.row_cap import shrink_row_cap
from mssql_analyst.tools.structural_validator import validate_sql_structure
from mssql_analyst.tools.validator import UnsafeSQLError, assert_select_only

logger = get_logger("mssql_analyst.graph.nodes")

# Default high-water mark for token-aware row-cap shrink.
_DEFAULT_HIGH_WATER_MARK = 30_000
# Floor for row-cap shrink (bound: never below this).
_DEFAULT_CAP_FLOOR = 100


def _now_ms() -> int:
    return int(time.perf_counter() * 1000)


def _append_timeline(
    state: AgentState,
    *,
    node: str,
    started_ms: int,
    duration_ms: int,
    extra: dict | None = None,
) -> None:
    """Append a timing entry to ``state["timelines"]`` in-place.

    Note: LangGraph merges the returned dict from each node into the
    state, so we mutate ``state["timelines"]`` directly here because the
    graph doesn't merge lists by reference.
    """
    entry = {"node": node, "started_ms": started_ms, "duration_ms": duration_ms}
    if extra:
        entry.update(extra)
    state.setdefault("timelines", []).append(entry)


# ---------------------------------------------------------------------------
# Factory: build node-bound callables for the graph runner
# ---------------------------------------------------------------------------


def build_nodes(
    *,
    llm: LLMClient,
    connector: MssqlConnector,
    schema_provider: Callable[[], dict[str, list[dict[str, str]]]],
    base_row_cap: int,
    high_water_mark: int = _DEFAULT_HIGH_WATER_MARK,
    cap_floor: int = _DEFAULT_CAP_FLOOR,
):
    """Return a dict of {node_name: callable} ready for the runner.

    ``base_row_cap`` is the un-shrunk row cap; the executor halves it
    once past ``high_water_mark``. ``cap_floor`` is the lower clamp.
    """

    def nl_to_sql(state: AgentState) -> AgentState:
        t0 = _now_ms()
        q = (state.get("question") or "").strip()
        if not q:
            duration = _now_ms() - t0
            _append_timeline(
                state,
                node="nl_to_sql",
                started_ms=t0,
                duration_ms=duration,
                extra={"error": "empty_question"},
            )
            return {"error": "empty_question", "status": "failed"}

        # Compose the user payload. On a retry (we have a
        # ``validation_complaints`` list from the previous cycle),
        # include them so the LLM can fold the feedback into its
        # response.
        try:
            schema = schema_provider()
            template = load_prompt("nl_to_sql")
            payload: dict[str, Any] = {
                "schema": schema,
                "question": q,
                "validation_complaints": list(
                    state.get("validation_complaints") or []
                ),
                "previous_sql": state.get("sql") or "",
                "is_retry": bool(state.get("validation_retry_pending")),
            }
            res = llm.call_json(
                prompt_name="nl_to_sql",
                template=template,
                user_payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            duration = _now_ms() - t0
            _append_timeline(
                state, node="nl_to_sql", started_ms=t0, duration_ms=duration,
                extra={"error": _public_message(exc)},
            )
            return _capture(state, exc, where="nl_to_sql")

        sql = _extract_sql(res.content)
        attempts = int(state.get("sql_attempts") or 0) + 1
        tokens = int(state.get("tokens_used") or 0) + int(res.total_tokens or 0)

        if not sql:
            duration = _now_ms() - t0
            _append_timeline(
                state, node="nl_to_sql", started_ms=t0, duration_ms=duration,
                extra={"error": "llm_returned_empty_sql", "attempts": attempts},
            )
            return {
                "sql": None,
                "sql_attempts": attempts,
                "tokens_used": tokens,
                "error": "llm_returned_empty_sql",
                "status": "failed",
                "validation_complaints": [],
                "validation_retry_pending": False,
            }
        try:
            assert_select_only(sql)
        except UnsafeSQLError as exc:
            # The SAFETY gate is non-recoverable — DDL/DML means the
            # LLM has fundamentally violated the contract. Surface
            # 400 immediately, no retry.
            duration = _now_ms() - t0
            _append_timeline(
                state, node="nl_to_sql", started_ms=t0, duration_ms=duration,
                extra={"error": _public_message(exc), "attempts": attempts},
            )
            return {
                "sql": sql,
                "sql_attempts": attempts,
                "tokens_used": tokens,
                "validation_error": str(exc),
                "error": f"unsafe_sql: {exc}",
                "status": "failed",
                "validation_complaints": [],
                "validation_retry_pending": False,
            }
        duration = _now_ms() - t0
        _append_timeline(
            state, node="nl_to_sql", started_ms=t0, duration_ms=duration,
            extra={"attempts": attempts, "tokens_in": int(res.total_tokens or 0)},
        )
        return {
            "sql": sql,
            "sql_attempts": attempts,
            "tokens_used": tokens,
            "validation_error": None,
            "validation_complaints": [],  # clear stale complaints from prev cycle
            "validation_retry_pending": False,
        }

    def validate_sql(state: AgentState) -> AgentState:
        t0 = _now_ms()
        sql = state.get("sql") or ""
        if not sql:
            duration = _now_ms() - t0
            _append_timeline(
                state, node="validate_sql", started_ms=t0, duration_ms=duration,
                extra={"clean": False, "reason": "no_sql"},
            )
            return {
                "validation_error": "no_sql",
                "validation_complaints": ["the LLM did not produce a SQL; try again with a clear SELECT"],
                "validation_retry_pending": True,
            }
        clean, complaints = validate_sql_structure(sql)
        duration = _now_ms() - t0
        _append_timeline(
            state, node="validate_sql", started_ms=t0, duration_ms=duration,
            extra={
                "clean": clean,
                "complaints": len(complaints),
            },
        )
        if not clean:
            return {
                "validation_error": "; ".join(complaints)[:500],
                "validation_complaints": complaints,
                "validation_retry_pending": True,
            }
        return {
            "validation_error": None,
            "validation_complaints": [],
            "validation_retry_pending": False,
        }

    def execute_sql(state: AgentState) -> AgentState:
        t0 = _now_ms()
        sql = state.get("sql") or ""
        if not sql:
            duration = _now_ms() - t0
            _append_timeline(
                state, node="execute_sql", started_ms=t0, duration_ms=duration,
                extra={"error": "no_sql"},
            )
            return {"error": "no_sql", "status": "failed"}
        # Phase-3 token-aware row-cap shrink. The base cap comes from
        # settings; we shrink once past the high-water mark.
        base_cap = max(1, int(base_row_cap))
        tokens = int(state.get("tokens_used") or 0)
        effective = shrink_row_cap(
            base_row_cap=base_cap,
            tokens_used=tokens,
            high_water_mark=high_water_mark,
            floor=cap_floor,
        )
        try:
            columns, rows, raw_count = connector.execute(sql)
            latency_ms = int(
                (state.get("latency_ms") or 0) + (_now_ms() - t0)
            )
        except Exception as exc:  # noqa: BLE001
            duration = _now_ms() - t0
            _append_timeline(
                state, node="execute_sql", started_ms=t0, duration_ms=duration,
                extra={"error": _public_message(exc), "row_cap_effective": effective},
            )
            return _capture(state, exc, where="execute_sql")

        duration = _now_ms() - t0
        _append_timeline(
            state, node="execute_sql", started_ms=t0, duration_ms=duration,
            extra={
                "row_count": int(raw_count),
                "row_cap_effective": effective,
                "tokens_at_exec": tokens,
            },
        )
        return {
            "columns": list(columns),
            "rows": [tuple(r) for r in rows],
            "row_count": int(raw_count),
            "latency_ms": latency_ms,
            "row_cap_effective": effective,
        }

    def finalize(state: AgentState) -> AgentState:
        # finalize intentionally does not log a timeline; nothing measurable.
        if state.get("status") == "failed":
            return {"status": "failed"}
        return {"status": "completed"}

    def handle_error(state: AgentState) -> AgentState:
        # Surface whatever error landed first as the public failure.
        return {
            "status": "failed",
            "error": state.get("error")
            or (state.get("validation_error") or "unknown_failure"),
        }

    return {
        "nl_to_sql": nl_to_sql,
        "validate_sql": validate_sql,
        "execute_sql": execute_sql,
        "finalize": finalize,
        "handle_error": handle_error,
    }


# ---------------------------------------------------------------------------
# Plain (unbound) node symbols — used by the unit graph test only.
# ---------------------------------------------------------------------------


def _nl_to_sql_unbound(state: AgentState) -> AgentState:
    return {**state, "validation_error": None}


def _execute_sql_unbound(state: AgentState) -> AgentState:
    return {**state, "row_count": 0}


def _validate_sql_unbound(state: AgentState) -> AgentState:
    return {**state, "validation_retry_pending": False}


def _finalize_unbound(state: AgentState) -> AgentState:
    return {
        **state,
        "status": "completed" if not state.get("error") else "failed",
    }


def _handle_error_unbound(state: AgentState) -> AgentState:
    return {**state, "status": "failed"}


# Aliases for the unbound nodes (unit graph test only).
nl_to_sql = _nl_to_sql_unbound
execute_sql = _execute_sql_unbound
validate_sql = _validate_sql_unbound
finalize = _finalize_unbound
handle_error = _handle_error_unbound


# ---------------------------------------------------------------------------
# Back-compat module-level singletons — Phase-1 integration tests monkeypatch
# ``nodes_mod.connector_singleton`` and ``nodes_mod.llm_singleton``. Phase 3
# passes them explicitly to ``build_nodes`` via ``run_agent``, but we keep
# these symbols so the Phase-1 fixture surface continues to work (they are
# read by ``runner.run_agent`` as a fall-back in case ``build_nodes`` was
# not yet wired).
# ---------------------------------------------------------------------------

llm_singleton: LLMClient | None = None
connector_singleton: MssqlConnector | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_sql(content: Any) -> str:
    if isinstance(content, dict):
        sql = content.get("sql") or content.get("SQL") or ""
        return str(sql).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def _capture(state: AgentState, exc: Exception, *, where: str) -> dict[str, Any]:
    logger.warning("graph_node_failed", extra={"where": where, "exc": repr(exc)})
    return {
        "error": _public_message(exc),
        "status": "failed",
    }


def _public_message(exc: Exception) -> str:
    msg = str(exc).strip()
    if not msg:
        msg = exc.__class__.__name__
    return msg[:300]
