"""Graph nodes for the CSV-aware query pipeline."""
from __future__ import annotations

import json
import re
import time

from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError
from src.observability.events import get_logger

log = get_logger("nodes")

MAX_ITERATIONS = 3


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from LLM output."""
    # try fenced block first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    blob = m.group(1) if m else text
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def node_plan(state: AgentState) -> AgentState:
    try:
        update: AgentState = {"plan": ["inspect schema", "generate sql", "execute", "evaluate"]}
        return update
    except Exception as exc:  # noqa: BLE001
        log.error("node_plan.failed", error=str(exc))
        return {"error": str(exc)}


def node_generate_sql(state: AgentState) -> AgentState:
    try:
        client = LLMClient()
        system = load_prompt("csv-query")
        schema = state.get("datasource_id", "csv-upload")
        question = state["question"]
        iteration = state.get("iteration", 0)

        user = f"Schema context: {schema}\n\nQuestion: {question}\n"
        if iteration > 0:
            user += (
                "\nThe previous attempt was insufficient. "
                "Return a corrected query with higher confidence.\n"
            )

        raw = client.complete(system, user, max_tokens=2048)
        parsed = _extract_json(raw) or {}

        sql = parsed.get("sql", "")
        code_display = parsed.get("code_display", sql)
        if not sql:
            # Fallback: ask LLM directly without JSON wrapper
            sql = raw.strip()

        return {
            "sql": sql,
            "code_display": code_display,
            "iteration": state.get("iteration", 0) + 1,
            "error": None,
        }
    except LLMError as exc:
        log.error("node_generate_sql.failed", error=str(exc))
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        log.error("node_generate_sql.failed", error=str(exc))
        return {"error": str(exc)}


def node_execute(state: AgentState) -> AgentState:
    try:
        from src.db.session import create_db_session
        from src.db.models import QueryRun
        from src.llm.tools.sql_execute import sql_execute  # Phase 1 tool

        sql = state.get("sql") or ""
        if not sql.strip():
            return {"error": "Empty SQL generated"}

        start = time.perf_counter()
        result = sql_execute(sql=sql, params={})
        latency_ms = int((time.perf_counter() - start) * 1000)

        # persist run row
        with create_db_session() as session:
            run = QueryRun(
                question=state.get("question", ""),
                datasource_id=state.get("datasource_id"),
                generated_sql=sql,
                result_columns=json.dumps(result.get("columns", [])),
                result_row_count=result.get("row_count", 0),
                latency_ms=latency_ms,
                status="success",
            )
            session.add(run)
            session.flush()
            state["run_id"] = run.id  # type: ignore[assignment]

        return {
            "sql_result": result,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        log.error("node_execute.failed", error=str(exc))
        return {"error": str(exc)}


def node_evaluate(state: AgentState) -> AgentState:
    try:
        question = state.get("question", "")
        result = state.get("sql_result") or {}
        rows = result.get("rows", [])
        row_count = result.get("row_count", 0)

        # simple heuristic confidence
        if row_count == 0 and "how many" in question.lower():
            confidence = 0.4
        elif row_count > 0:
            confidence = 0.9
        else:
            confidence = 0.5

        return {
            "evaluate_score": confidence,
            "checkpoint": "evaluated",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        log.error("node_evaluate.failed", error=str(exc))
        return {"error": str(exc)}


def node_finalize(state: AgentState) -> AgentState:
    try:
        client = LLMClient()
        system = (
            "You are a careful data analyst. Produce a concise, accurate natural-language "
            "answer from the question, the SQL that was run, and the result set. "
            "Do not invent data that is not present."
        )
        question = state.get("question", "")
        sql = state.get("code_display") or state.get("sql") or ""
        result = state.get("sql_result") or {}
        columns = result.get("columns", [])
        rows = result.get("rows", [])[:50]

        user = (
            f"Question: {question}\n\n"
            f"SQL executed:\n```sql\n{sql}\n```\n\n"
            f"Result columns: {columns}\n"
            f"Result rows (sample, max 50): {json.dumps(rows)}\n"
        )
        answer = client.complete(system, user, max_tokens=1024)

        return {
            "answer": answer,
            "checkpoint": "finalized",
            "error": None,
            "status": "completed",
        }
    except LLMError as exc:
        log.error("node_finalize.failed", error=str(exc))
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        log.error("node_finalize.failed", error=str(exc))
        return {"error": str(exc)}


def handle_error(state: AgentState) -> AgentState:
    log.error("agent.error", error=state.get("error"))
    return {"status": "failed"}
