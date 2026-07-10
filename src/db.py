"""SQLite persistence for podcast sessions (single-user, local)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                topic       TEXT NOT NULL,
                hosts       TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'generating',
                audio_path  TEXT,
                error       TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_session(session_id: str, topic: str, hosts: list[str], audio_path: str) -> None:
    now = _now()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (id, topic, hosts, status, audio_path, created_at, updated_at) "
            "VALUES (?, ?, ?, 'generating', ?, ?, ?)",
            (session_id, topic, _json(hosts), audio_path, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def update_status(session_id: str, status: str, error: str | None = None,
                  audio_path: str | None = None) -> None:
    now = _now()
    conn = get_conn()
    try:
        if audio_path is not None:
            conn.execute(
                "UPDATE sessions SET status=?, error=?, audio_path=?, updated_at=? WHERE id=?",
                (status, error, audio_path, now, session_id),
            )
        else:
            conn.execute(
                "UPDATE sessions SET status=?, error=?, updated_at=? WHERE id=?",
                (status, error, now, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_session(session_id: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _json(x) -> str:
    import json
    return json.dumps(x)
