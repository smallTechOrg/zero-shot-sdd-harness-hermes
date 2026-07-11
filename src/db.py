"""SQLite mastery store — private per-student notation-mastery state only.

No other data is persisted. Mastery uses a simple Leitner-style weight:
correct answers raise a topic's weight, misses lower it. Lower-weight topics
are sampled more often by the drill selector.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = os.environ.get("AGENT_DATABASE_URL", "").replace("sqlite:///", "") or str(
    Path(__file__).resolve().parent.parent.parent / "data" / "music_tutor.db"
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id           TEXT PRIMARY KEY,
    display_name TEXT,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mastery (
    id          TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL,
    topic       TEXT NOT NULL,
    weight      REAL NOT NULL DEFAULT 0.3,
    attempts    INTEGER NOT NULL DEFAULT 0,
    correct     INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL,
    UNIQUE(student_id, topic)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def ensure_student(student_id: str, display_name: str | None = None) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO students(id, display_name, created_at) "
            "VALUES (?, ?, ?)",
            (student_id, display_name, _now()),
        )


def record_result(student_id: str, topic: str, correct: bool) -> None:
    """Update mastery for a topic after an attempt."""
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO mastery(id, student_id, topic, weight, "
            "attempts, correct, updated_at) VALUES (?, ?, ?, 0.3, 0, 0, ?)",
            (f"{student_id}:{topic}", student_id, topic, _now()),
        )
        delta = 0.12 if correct else -0.18
        c.execute(
            "UPDATE mastery SET attempts = attempts + 1, "
            "correct = correct + ?, weight = MIN(1.0, MAX(0.05, weight + ?)), "
            "updated_at = ? WHERE student_id = ? AND topic = ?",
            (1 if correct else 0, delta, _now(), student_id, topic),
        )


def get_mastery(student_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT topic, weight, attempts, correct FROM mastery "
            "WHERE student_id = ? ORDER BY topic",
            (student_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def weight_for(student_id: str, topic: str) -> float:
    with _conn() as c:
        row = c.execute(
            "SELECT weight FROM mastery WHERE student_id = ? AND topic = ?",
            (student_id, topic),
        ).fetchone()
    return row["weight"] if row else 0.3
