"""Graph nodes — CSV data analyst capability.

Follows the baseline contract: ``(state) -> partial state``; failures go
into ``state["error"]`` so the error edge routes to handle_error.
"""

from __future__ import annotations

import json
import time

from src.graph.state import AgentState
from src.graph.tools import execute_sql_safe, schema_tool
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError


def _update_state(state: AgentState, **kwargs) -> AgentState:
    updated = dict(state)
    updated.update(kwargs)
    return updated


def plan_query(state: AgentState) -> AgentState:
    try:
        client = LLMClient()
        schema = state.get("schema_markdown")
        if not schema:
            schema_raw = schema_tool(
                session_id=state.get("session_id") or "",
                data_source=state.get("data_source", "cache"),
            )
            schema = schema_raw.get("markdown", "")

        system = load_prompt("query")
        user_parts = [
            "## Schema\n",
            schema or "(no tables available)",
            "\n\n## Question\n",
            state.get("question", ""),
            "\n\nReturn JSON with keys: sql, chart_spec, suggestions.",
        ]
        user = "".join(user_parts)

        raw = client.complete(system, user, max_tokens=2048)
        parsed = _parse_plan(raw)
        return _update_state(
            state,
            schema_markdown=schema,
            sql=parsed.get("sql"),
            chart_spec=parsed.get("chart_spec"),
            suggestions=parsed.get("suggestions"),
            provider=client.provider_name,
            model=client.model,
            error=None,
        )
    except LLMError as exc:
        return _update_state(state, error=str(exc))


def _parse_plan(raw: str) -> dict:
    # best-effort JSON parsing: strip markdown code fences, then json.loads.
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            text = "\n".join(lines[1:])
        if lines and lines[-1].startswith("```"):
            text = "\n".join(lines[:-1])
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    sql = data.get("sql")
    if not isinstance(sql, str):
        sql = None
    chart = data.get("chart_spec")
    if isinstance(chart, dict):
        chart_spec = chart
    else:
        chart_spec = None
    suggestions = data.get("suggestions")
    if isinstance(suggestions, list) and all(isinstance(x, str) for x in suggestions):
        suggestions_list = suggestions
    else:
        suggestions_list = []
    return {
        "sql": sql,
        "chart_spec": chart_spec,
        "suggestions": suggestions_list,
    }


def execute_tool(state: AgentState) -> AgentState:
    if not state.get("sql"):
        return _update_state(state, tool_error="No SQL was generated from the question.")
    try:
        result = execute_sql_safe(
            session_id=state.get("session_id") or "",
            sql=state["sql"],
            data_source=state.get("data_source", "cache"),
            max_rows=10_000,
        )
        return _update_state(state, query_result=result, tool_error=None)
    except Exception as exc:
        return _update_state(state, tool_error=str(exc))


def finalize(state: AgentState) -> AgentState:
    question = state.get("question", "")
    sql = state.get("sql")
    query_result = state.get("query_result")
    tool_error = state.get("tool_error")
    chart_spec = state.get("chart_spec")
    suggestions = state.get("suggestions") or []
    data_source = state.get("data_source", "cache")

    if tool_error:
        output = {
            "answer": "I couldn't run the query successfully.",
            "error": tool_error,
            "sql": sql,
            "chart": None,
            "source": data_source,
            "suggestions": [_fallback_suggestion(question)],
        }
        return _update_state(
            state,
            output_text=json.dumps(output),
            status="completed",
            error=None,
        )

    columns = []
    rows = []
    row_count = 0
    latency_ms = 0
    if isinstance(query_result, dict):
        columns = query_result.get("columns", [])
        rows = query_result.get("rows", [])
        row_count = query_result.get("row_count", 0)
        latency_ms = query_result.get("latency_ms", 0)

    provider = state.get("provider")
    model = state.get("model")
    latency_total = (state.get("latency_ms") or 0) + latency_ms

    chart = _render_chart(columns, rows, chart_spec)

    answer = _build_answer(question, sql, columns, rows, row_count, chart_spec)
    output = {
        "answer": answer,
        "sql": sql,
        "table": {"columns": columns, "rows": rows[:1000], "row_count": row_count},
        "chart": chart,
        "source": data_source,
        "latency_ms": latency_total,
        "provider": provider,
        "model": model,
        "suggestions": suggestions,
    }
    return _update_state(
        state,
        output_text=json.dumps(output),
        status="completed",
        latency_ms=latency_total,
        error=None,
    )


def _fallback_suggestion(question: str) -> str:
    return "Try uploading a sample CSV for me to inspect, or rephrase the question using exact column names."


def _build_answer(
    question: str,
    sql: str,
    columns: list[str],
    rows: list,
    row_count: int,
    chart_spec: dict | None,
) -> str:
    if not rows:
        return f"I couldn't find any rows matching that question. The generated SQL was valid but returned an empty result."
    try:
        from src.graph.tools import cache_query, live_query, live_schema  # noqa: F401
    except Exception:
        pass
    first_row = rows[0]
    preview = ", ".join(f"{col}={first_row[idx]}" for idx, col in enumerate(columns[:5]))
    chart_line = (
        f"\n\nI generated a chart recommendation for this data: {json.dumps(chart_spec) if chart_spec else 'none'}."
    )
    return (
        f"From the data I found {row_count} row(s). "
        f"Top row: {preview}. "
        f"I ran this SQL: {sql}"
        f"{chart_line}"
    )


def _render_chart(columns: list[str], rows: list, chart_spec: dict | None) -> dict | None:
    if not rows or not columns:
        return None
    chart = chart_spec or {}
    kind = chart.get("type", "bar")
    if kind not in {"bar", "line", "pie"}:
        kind = "bar"
    label_col = chart.get("x") or columns[0]
    value_col = chart.get("y")
    if not value_col:
        for col in columns[1:4]:
            if any(isinstance(r[idx], (int, float)) for idx, r in enumerate(zip(*rows[: len(columns)]))):
                value_col = col
                break
    if not value_col:
        return None

    try:
        x_index = columns.index(label_col)
    except ValueError:
        return None
    try:
        y_index = columns.index(value_col)
    except ValueError:
        return None

    values = []
    for row in rows[:50]:
        values.append(row[y_index])
    labels = [str(row[x_index]) for row in rows[:50]]

    traces = [
        {
            "type": kind,
            "name": value_col,
            "x": labels,
            "y": values,
        }
    ]
    return {"data": traces, "layout": {"title": f"{value_col} by {label_col}", "autosize": True}}


def handle_error(state: AgentState) -> AgentState:
    return _update_state(state, status="failed")
