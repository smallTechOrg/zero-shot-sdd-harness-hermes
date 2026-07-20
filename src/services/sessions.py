"""Session service — create, fetch, ingest CSVs, schema summary."""
from __future__ import annotations

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.db.models import SessionRow
from src.db.session import create_db_session

MAX_CSV_BYTES = 100 * 1024 * 1024


def session_db_path(session_id: str) -> Path:
    base = Path(get_settings().duckdb_dir) / "sessions"
    return base / session_id / "session.duckdb"


def _table_name(filename: str) -> str:
    stem = Path(filename).stem
    return "".join(c if c.isalnum() or c == "_" else "_" for c in stem).lower().strip("_") or "upload"


def create_session() -> SessionRow:
    with create_db_session() as db:
        row = SessionRow()
        db.add(row)
        db.flush()
        db.refresh(row)
        db.expunge(row)
        return row


def get_session_row(session_id: str) -> SessionRow | None:
    with create_db_session() as db:
        row = db.get(SessionRow, session_id)
        if row is not None:
            db.expunge(row)
        return row


def _ingest_single(conn: Any, table: str, raw: bytes) -> int:
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return 0
    cols = list(rows[0].keys())

    # Infer DuckDB types from sample values so numeric columns are INTEGER/DOUBLE.
    # Without this, SUM(value) on all-TEXT columns raises a type error that the
    # LLM doesn't recover from cleanly and the run returns 0 rows.
    col_types: list[str] = ["TEXT"] * len(cols)
    sample_size = min(len(rows), 200)
    for ci, col in enumerate(cols):
        has_int = False
        has_float = False
        for ri in range(sample_size):
            raw_val = rows[ri].get(col)
            if raw_val in (None, ""):
                continue
            try:
                float(raw_val)
                # Detect floats with a decimal point or exponent
                if any(c in raw_val for c in (".", "e", "E")):
                    has_float = True
                else:
                    has_int = True
            except ValueError:
                pass
        if has_float:
            col_types[ci] = "DOUBLE"
        elif has_int:
            col_types[ci] = "INTEGER"

    col_defs = ", ".join(f'"{c}" {t}' for c, t in zip(cols, col_types))
    conn.execute(f'CREATE OR REPLACE TABLE "{table}" ({col_defs})')
    for row in rows:
        values = ", ".join(
            f"'{str(v).replace(chr(39), chr(39)+chr(39))}'" if v is not None else "NULL"
            for v in row.values()
        )
        conn.execute(f"INSERT INTO \"{table}\" VALUES ({values})")
    return len(rows)


def ingest_csvs(session_id: str, files: list[tuple[str, bytes]]) -> tuple[dict[str, Any], list[str]]:
    db_path = session_db_path(session_id)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import duckdb
    conn = duckdb.connect(str(db_path), read_only=False)
    try:
        tables: list[dict[str, Any]] = []
        errors: list[str] = []
        table_counter: dict[str, int] = {}
        for filename, raw in files:
            if len(raw) > MAX_CSV_BYTES:
                errors.append(f"{filename}: too large")
                continue
            table = _table_name(filename)
            table_counter[table] = table_counter.get(table, 0) + 1
            if table_counter[table] > 1:
                table = f"{table}_{table_counter[table]}"
            try:
                count = _ingest_single(conn, table, raw)
                tables.append({"table": table, "filename": filename, "row_count": count})
            except Exception as exc:
                errors.append(f"{filename}: {exc}")
        payload = {"tables": tables, "errors": errors}
        with create_db_session() as db:
            row = db.get(SessionRow, session_id)
            if row is not None:
                row.schema_summary = json.dumps(payload)
                db.add(row)
        return payload, errors
    finally:
        conn.close()


def schema_summary(session_id: str) -> dict[str, Any]:
    row = get_session_row(session_id)
    if not row or not row.schema_summary:
        return {"tables": []}
    try:
        return json.loads(row.schema_summary)
    except Exception:
        return {"tables": []}
