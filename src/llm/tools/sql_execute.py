"""SQL execution tools — CSV-backed (SQLite/pandas) and MsSQL (pyodbc) paths."""
from __future__ import annotations

import os
import re
import sqlite3
import time
from typing import Any

import pandas as pd
from src.observability.events import get_logger

log = get_logger("sql_tools")

MAX_ROWS_RETURN = 10000


def _is_safe_sql(sql: str) -> bool:
    """Block DDL/DML for read-only enforcement."""
    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|SP_)\b", re.IGNORECASE)
    return not forbidden.search(sql) if sql else True


def sql_execute(sql: str, params: dict | None = None, *, db_path: str = "./data/app.db", datasource_type: str = "sqlite") -> dict[str, Any]:
    """Execute a read-only SQL query against the active datasource.

    - Default path uses a SQLite DB whose tables mirror uploaded CSVs.
    - MsSQL path calls pyodbc; column naming/schema handled upstream.
    """
    start = time.perf_counter()
    try:
        if not _is_safe_sql(sql):
            return {"columns": [], "rows": [], "row_count": 0, "latency_ms": 0, "error": "Unsafe SQL: write operations are blocked"}

        if datasource_type == "sqlite":
            if not os.path.exists(db_path):
                return {"columns": [], "rows": [], "row_count": 0, "latency_ms": 0, "error": f"DB file not found: {db_path}"}
            con = sqlite3.connect(db_path)
            try:
                df = pd.read_sql_query(sql, con, params=params)
            finally:
                con.close()
        elif datasource_type == "mssql":
            # Phase 2 integration point; kept as no-op placeholder for Phase 1 compile.
            return {"columns": [], "rows": [], "row_count": 0, "latency_ms": 0, "error": "MsSQL not wired yet"}
        else:
            return {"columns": [], "rows": [], "row_count": 0, "latency_ms": 0, "error": f"Unknown datasource_type: {datasource_type}"}

        if len(df) > MAX_ROWS_RETURN:
            df = df.head(MAX_ROWS_RETURN)

        rows = df.where(pd.notnull(df), None).values.tolist()
        columns = list(df.columns)
        latency_ms = int((time.perf_counter() - start) * 1000)

        return {
            "columns": columns,
            "rows": rows,
            "row_count": int(len(df)),
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001
        log.error("sql_execute.failed", error=str(exc), sql=sql[:500])
        return {"columns": [], "rows": [], "row_count": 0, "latency_ms": int((time.perf_counter() - start) * 1000), "error": str(exc)}


def datasource_info(*, db_path: str = "./data/app.db", datasource_type: str = "sqlite") -> dict[str, Any]:
    """Return lightweight schema summary for the active datasource."""
    if datasource_type != "sqlite" or not os.path.exists(db_path):
        return {"datasource": datasource_type, "tables": []}
    try:
        con = sqlite3.connect(db_path)
        try:
            tables = [
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            info = []
            for t in tables[:100]:
                cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")').fetchall()]
                cnt = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                info.append({"name": t, "columns": cols, "row_count": cnt})
        finally:
            con.close()
        return {"datasource": datasource_type, "tables": info}
    except Exception as exc:  # noqa: BLE001
        log.error("datasource_info.failed", error=str(exc))
        return {"datasource": datasource_type, "tables": [], "error": str(exc)}
