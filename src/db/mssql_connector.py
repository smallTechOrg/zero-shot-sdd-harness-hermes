"""MsSQL connector — read-replica only. Graceful absence: if pyodbc / DSN
are not configured, the module imports cleanly and all functions raise
ConnectionError, letting the API surface a clear message to the user."""
from __future__ import annotations

import os
from typing import Any

try:
    import pyodbc  # type: ignore[import-untyped]

    _pyodbc = True
except ImportError:
    _pyodbc = False

_MAX_ROWS = 10_000


def _conn_str() -> str:
    return os.environ.get("AGENT_MSSQL_CONNECTION_STRING", "")


def test_connection() -> dict:
    conn_str = _conn_str()
    if not conn_str:
        raise ConnectionError(
            "AGENT_MSSQL_CONNECTION_STRING is not set. "
            "Set it in .env to enable live DB queries."
        )
    if not _pyodbc:
        raise ConnectionError(
            "pyodbc is not installed. Run: uv add pyodbc (requires ODBC driver installed)."
        )
    import time

    t0 = time.perf_counter()
    try:
        with pyodbc.connect(conn_str, timeout=5) as con:
            db = con.getinfo(pyodbc.SQL_DATABASE_NAME)
            tables: int = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_type='BASE TABLE'"
            ).fetchone()[0]
    except Exception as exc:
        raise ConnectionError(f"MsSQL connection failed: {exc}") from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {"connected": True, "database": db, "tables_count": tables, "latency_ms": latency_ms}


def live_schema(database: str | None = None) -> list[dict[str, Any]]:
    if not _pyodbc:
        raise ConnectionError("pyodbc not installed")
    conn_str = _conn_str()
    if database:
        # optional override via AGENT_MSSQL_DATABASE (less common; conn_str is primary)
        pass
    result: list[dict[str, Any]] = []
    with pyodbc.connect(conn_str, timeout=5) as con:
        rows = con.execute(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.tables "
            "WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME"
        ).fetchall()
        for schema, table in rows:
            full = f"{schema}.{table}"
            cols = [
                {"name": r[0], "type": r[1]}
                for r in con.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                    "WHERE TABLE_SCHEMA=? AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                    schema,
                    table,
                ).fetchall()
            ]
            result.append({"name": full, "row_count": None, "columns": cols, "schema": schema})
    return result


def live_query(sql: str, max_rows: int = _MAX_ROWS) -> dict:
    if not _pyodbc:
        raise ConnectionError("pyodbc not installed")
    import time

    t0 = time.perf_counter()
    try:
        with pyodbc.connect(_conn_str(), timeout=10) as con:
            cur = con.execute(sql)
            if cur.description is None:
                columns, rows = [], []
            else:
                columns = [d[0] for d in cur.description]
                fetched = cur.fetchall()
                if len(fetched) > max_rows:
                    raise ValueError(
                        f"Result has {len(fetched)} rows; maximum allowed is {max_rows}."
                    )
                rows = [list(r) for r in fetched]
    except Exception as exc:
        raise ValueError(f"MsSQL query error: {exc}") from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return {"columns": columns, "rows": rows, "row_count": len(rows), "latency_ms": latency_ms}
