"""Execute DuckDB SQL for a CSV session."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from src.config.settings import get_settings


def session_db_path(session_id: str) -> Path:
    base = Path(get_settings().duckdb_dir) / "sessions"
    return base / session_id / "session.duckdb"


def execute_sql(session_id: str, sql: str, limit: int = 500) -> tuple[list[dict[str, object]], float, str]:
    import duckdb
    t0 = time.perf_counter()
    db_path = session_db_path(session_id)
    if not db_path.exists():
        raise FileNotFoundError(f"Session database not found: {db_path}")
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute(sql).fetchall()
        cols = [d[0] for d in (conn.description or [])]
        data = [dict(zip(cols, row)) for row in rows[:limit]]
    finally:
        conn.close()
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    payload = json.dumps(data, sort_keys=True, default=str).encode()
    result_hash = hashlib.sha256(payload).hexdigest()
    return data, latency_ms, result_hash
