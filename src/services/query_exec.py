"""Query execution service — DuckDB backed by session files."""
from __future__ import annotations

from pathlib import Path

from src.config.settings import get_settings


def _session_db_path(session_id: str) -> Path:
    return Path(get_settings().duckdb_dir) / "sessions" / session_id / "session.duckdb"


def execute_sql(session_id: str, sql: str) -> list[dict]:
    import duckdb

    db_path = _session_db_path(session_id)
    if not db_path.exists():
        raise FileNotFoundError(f"Session database not found: {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(sql).fetchall()
        cols = [d[0] for d in (conn.description or [])]
        return [dict(zip(cols, row)) for row in rows]
    finally:
        conn.close()
