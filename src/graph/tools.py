"""Tool layer — functions exposed to the LangGraph ToolNode.

Safety contract:
- Never allow DDL / DML side-effects (DROP/DELETE/TRUNCATE/ALTER/INSERT/UPDATE/EXEC).
- Enforce max_rows before returning large result sets.
- Route to DuckDB (cache) or MsSQL (live) based on `data_source`.

All functions return a dict; exceptions are surfaced via `handle_error` in the graph.
"""
from __future__ import annotations

import re

from src.db.duckdb_store import schema_to_markdown as cache_schema_md
from src.db.duckdb_store import get_schema as cache_schema
from src.db.duckdb_store import query as cache_query
from src.db.mssql_connector import live_query, live_schema, test_connection

_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE|EXEC|EXECUTE|MERGE)\b",
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> None:
    if _FORBIDDEN.search(sql):
        raise ValueError(
            "Only read-only queries are allowed. "
            "Found forbidden keyword in SQL — queries may only contain SELECT, WITH, ORDER BY, GROUP BY, HAVING, JOIN, WHERE, LIMIT."
        )


def schema_tool(session_id: str, data_source: str = "cache") -> dict:
    """Return schema summary as markdown. Used as LLM context."""
    if data_source == "live":
        try:
            tables = live_schema()
        except Exception as exc:
            return {"error": str(exc)}
        lines = ["## Available tables (MsSQL live)\n"]
        for t in tables:
            lines.append(f"### {t['name']}")
            cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
            lines.append(f"Columns: {cols}\n")
        return {"markdown": "\n".join(lines), "tables": tables}
    tables = cache_schema(session_id)
    return {"markdown": cache_schema_md(tables), "tables": tables}


def execute_sql_safe(
    session_id: str, sql: str, data_source: str = "cache", max_rows: int = 10_000
) -> dict:
    """Execute a read-only SQL query. Returns result dict or raises."""
    _validate_sql(sql)
    if data_source == "live":
        return live_query(sql, max_rows=max_rows)
    return cache_query(session_id, sql, max_rows=max_rows)


def db_health() -> dict:
    """Check MsSQL connection health (used by /api/v1/db/test-connection)."""
    try:
        info = test_connection()
        info["available"] = True
        return info
    except Exception as exc:
        return {"available": False, "error": str(exc)}
