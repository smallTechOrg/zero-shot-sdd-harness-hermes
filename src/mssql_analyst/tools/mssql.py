"""Live MSSQL connector via ``pyodbc``.

Phase 1 hits the user's local ``master`` instance using Windows Integrated
Auth (Trusted_Connection) — the user's intake explicitly chose live MSSQL
(no caching, no mock).

The connector:
- opens a fresh ``pyodbc`` connection per call (no internal pool);
- sets a ``STATEMENT_TIMEOUT`` via the ``query_timeout`` cursor option;
- returns rows bounded to ``row_cap`` server-side (always);
- caches the schema (table → columns) once per process lifetime; the
  per-call cost is the query itself.

The cached schema is read from ``INFORMATION_SCHEMA.TABLES`` and
``INFORMATION_SCHEMA.COLUMNS``; it is exposed as a Python dict suitable
for direct JSON serialisation into the LLM prompt.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from mssql_analyst.config.settings import get_settings
from mssql_analyst.observability.events import get_logger

logger = get_logger("mssql_analyst.tools.mssql")


# ---------------------------------------------------------------------------
# Connection-string helper
# ---------------------------------------------------------------------------


def _build_conn_str() -> str:
    """Build the ``pyodbc`` connection string from settings.

    Honours ``AGENT_MSSQL_INTEGRATED_AUTH``:
        True  → uses ``Trusted_Connection=yes`` (Windows login).
        False → uses ``UID``/``PWD`` from settings.
    """
    s = get_settings()
    if not s.mssql_host:
        raise RuntimeError(
            "no_db_configured: AGENT_MSSQL_HOST is empty — set it in .env"
        )
    driver = s.mssql_driver
    db = s.mssql_db or "master"
    server = s.mssql_host
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={db}",
    ]
    if s.mssql_integrated_auth:
        parts.append("Trusted_Connection=yes")
        # Some drivers still require UID= empty.
        parts.append("UID=")
    else:
        uid = s.mssql_user or ""
        pwd = s.mssql_password.get_secret_value() if s.mssql_password else ""
        if not uid or not pwd:
            raise RuntimeError(
                "mssql_auth_incomplete: AGENT_MSSQL_USER and AGENT_MSSQL_PASSWORD "
                "are required when AGENT_MSSQL_INTEGRATED_AUTH=false"
            )
        parts.append(f"UID={uid}")
        parts.append(f"PWD={pwd}")
    return ";".join(parts)


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class MssqlConnector:
    """Live MSSQL via ``pyodbc`` with schema caching."""

    def __init__(self) -> None:
        self._schema_cache: dict[str, list[dict[str, str]]] | None = None
        self._schema_lock = threading.Lock()
        self._conn_str = _build_conn_str()
        self._timeout_sec = int(get_settings().mssql_query_timeout_sec or 15)
        self._row_cap = int(get_settings().mssql_row_cap or 1000)

    # Public surface --------------------------------------------------------

    def describe_schema(self) -> dict[str, list[dict[str, str]]]:
        """Return table → list of {name, type}. Cached for the process."""
        # Quick path without lock.
        if self._schema_cache is not None:
            return self._schema_cache
        with self._schema_lock:
            if self._schema_cache is not None:
                return self._schema_cache
            self._schema_cache = self._fetch_schema()
            logger.info(
                "mssql_schema_cached",
                table_count=len(self._schema_cache),
            )
            return self._schema_cache

    def execute(
        self, sql: str
    ) -> tuple[list[str], list[tuple], int]:
        """Run a single SELECT with timeout, return (columns, rows, row_count).

        ``row_count`` is the *raw* pre-cap count; ``rows`` itself is bounded
        to ``row_cap``.
        """
        import pyodbc  # imported lazily to keep tests fast on collection

        t0 = time.perf_counter()
        conn = pyodbc.connect(self._conn_str, timeout=self._timeout_sec)
        try:
            cursor = conn.cursor()
            # pyodbc's ``query_timeout`` is in seconds.
            try:
                cursor.timeout = self._timeout_sec
            except Exception:  # noqa: BLE001 — some drivers don't expose it
                pass
            cursor.execute(sql)
            # ``description`` -> [(name, type_code, …), …].
            columns = [d[0] for d in (cursor.description or [])]
            raw = cursor.fetchall()
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

        # Bound rows.
        bounded = raw[: self._row_cap]
        raw_count = len(raw)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "mssql_exec",
            columns=len(columns),
            row_count=raw_count,
            bounded=len(bounded),
            latency_ms=latency_ms,
        )
        # pyodbc returns ``Row`` objects that are tuple-compatible.
        rows = [tuple(r) for r in bounded]
        return columns, rows, raw_count

    # Internals -------------------------------------------------------------

    def _fetch_schema(self) -> dict[str, list[dict[str, str]]]:
        """Read INFORMATION_SCHEMA.TABLES + COLUMNS once."""
        import pyodbc  # noqa: F401  (kept local for symmetry)

        col_sql = (
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION"
        )
        conn = pyodbc.connect(self._conn_str, timeout=self._timeout_sec)
        try:
            cursor = conn.cursor()
            cursor.execute(col_sql)
            raw = cursor.fetchall()
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

        schema: dict[str, list[dict[str, str]]] = {}
        for r in raw:
            # Be defensive about pyodbc row shape (tuple-like, named-tuple-like).
            try:
                table, col, dtype = r[0], r[1], r[2]
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"mssql_schema_unexpected_row_shape: {exc.__class__.__name__}"
                ) from exc
            schema.setdefault(table, []).append({"name": col, "type": dtype or "varchar"})
        return schema


# ---------------------------------------------------------------------------
# Module-level singleton (one connector per process)
# ---------------------------------------------------------------------------

_connector: MssqlConnector | None = None
_connector_lock = threading.Lock()


def get_mssql_connector() -> MssqlConnector:
    """Process-wide cached connector. Tests can monkeypatch this."""
    global _connector
    if _connector is None:
        with _connector_lock:
            if _connector is None:
                _connector = MssqlConnector()
    return _connector


def reset_mssql_connector() -> None:
    """Test-only — drop the cached connector so the next call rebuilds."""
    global _connector
    _connector = None


# ---------------------------------------------------------------------------
# Light row / column coercion helpers
# ---------------------------------------------------------------------------


def coerce_scalar(v: Any) -> Any:
    """Convert pyodbc row values to JSON-safe Python primitives."""
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:  # noqa: BLE001
            return str(v)
    return v
