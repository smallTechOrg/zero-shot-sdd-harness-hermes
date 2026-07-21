"""Read-only MsSQL connector + local cache for Phase 2."""
from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from src.config.settings import get_settings


def _mssql_url() -> str | None:
    url = (get_settings().database_url_mssql or "").strip()
    return url or None


def has_mssql() -> bool:
    return _mssql_url() is not None


def _query_hash(question: str) -> str:
    return sha256(question.encode("utf-8")).hexdigest()[:16]


_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"


def _cache_db_path() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / "query_cache.sqlite3"


def cache_get(question: str) -> dict[str, Any] | None:
    key = _query_hash(question)
    with sqlite3.connect(_cache_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT data, expires_at FROM cache WHERE key=?", (key,)
        ).fetchone()
        if not row:
            return None
        import datetime as dt

        if row["expires_at"] and dt.datetime.now(
            dt.timezone.utc
        ) > dt.datetime.fromisoformat(row["expires_at"]):
            conn.execute("DELETE FROM cache WHERE key=?", (key,))
            conn.commit()
            return None
        return json.loads(row["data"])


def cache_set(
    question: str,
    payload: dict[str, Any],
    ttl_seconds: int = 3600,
) -> None:
    key = _query_hash(question)
    import datetime as dt

    expires = (
        dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=ttl_seconds)
    ).isoformat()
    with sqlite3.connect(_cache_db_path()) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, data TEXT, expires_at TEXT)"
        )
        conn.execute(
            "REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(payload), expires),
        )
        conn.commit()


def live_query(
    sql: str,
    *,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    url = _mssql_url()
    if not url:
        raise RuntimeError("AGENT_DATABASE_URL_MSSQL is not configured.")
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        stmt = text(sql)
        rows = conn.execute(stmt, params or {})
        return [dict(row._mapping) for row in rows]
