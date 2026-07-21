"""DuckDB cache — one .duckdb file stores all uploaded CSVs as tables."""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import duckdb

_CACHE_DIR = Path(os.environ.get("AGENT_DUCKDB_DIR", "data/duckdb"))
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


def _db_path(session_id: str) -> str:
    return str(_CACHE_DIR / f"{session_id}.duckdb")


def init_session(session_id: str) -> None:
    """Create an empty DuckDB file for a new session."""
    p = _db_path(session_id)
    with duckdb.connect(p, read_only=False) as con:
        con.execute("SELECT 1")


def ingest_csv(session_id: str, table_name: str, csv_bytes: bytes) -> dict:
    """Load a CSV into DuckDB under `table_name`. Returns table info."""
    p = _db_path(session_id)
    with _lock:
        with duckdb.connect(p, read_only=False) as con:
            con.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(csv_bytes)
                tmp_path = tmp.name
            try:
                con.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
                    (tmp_path,),
                )
            finally:
                os.unlink(tmp_path)
            row_count: int = con.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]
            cols: list[dict[str, str]] = [
                {"name": r[0], "type": r[1]}
                for r in con.execute(f"DESCRIBE {table_name}").fetchall()
            ]
    return {"name": table_name, "row_count": row_count, "columns": cols}


def get_schema(session_id: str) -> list[dict[str, Any]]:
    p = _db_path(session_id)
    if not Path(p).exists():
        return []
    with duckdb.connect(p, read_only=True) as con:
        tables: list[str] = [
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
        ]
        result: list[dict[str, Any]] = []
        for t in tables:
            cols = [
                {"name": r[0], "type": r[1]}
                for r in con.execute(f"DESCRIBE {t}").fetchall()
            ]
            rc = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            result.append({"name": t, "row_count": rc, "columns": cols})
    return result


def schema_to_markdown(schema: list[dict]) -> str:
    lines = ["## Available tables (DuckDB cache)\n"]
    for t in schema:
        lines.append(f"### {t['name']} ({t['row_count']} rows)")
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
        lines.append(f"Columns: {cols}\n")
    return "\n".join(lines)


def query(session_id: str, sql: str, max_rows: int = 10_000) -> dict:
    import time

    p = _db_path(session_id)
    if not Path(p).exists():
        raise ValueError(f"No cache for session {session_id!r}")
    t0 = time.perf_counter()
    with duckdb.connect(p, read_only=True) as con:
        try:
            cur = con.execute(sql)
        except duckdb.IOException as exc:
            raise ValueError(f"SQL error: {exc}") from exc
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
        latency_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "latency_ms": latency_ms,
    }
