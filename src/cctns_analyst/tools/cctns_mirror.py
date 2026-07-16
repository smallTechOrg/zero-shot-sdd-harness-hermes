"""CCTNS mirror abstraction.

Two implementations sit behind one factory:

- ``MockMirror`` — in-process, deterministic, seeded with ≥ 500 synthetic FIR
  rows. Default in dev when ``CCTNS_MIRROR_URL`` is unset.
- ``MssqlMirror`` (Phase 3) — SQL Server via pyodbc, points at
  ``cctns_mirror`` schema.

Both expose:

- ``list_tables() -> dict`` — schema only (table → list of {name, type}).
- ``execute(sql, *, row_cap, statement_timeout_ms) -> (columns, rows, raw_count)``.

The factory ``get_mirror_runner()`` returns ``(executor, schema_provider)``
matching the call sites in ``graph/runner.py``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from cctns_analyst.config.settings import get_settings

logger = logging.getLogger("cctns_analyst.tools.cctns_mirror")


# ---------------------------------------------------------------------------
# Abstract surface
# ---------------------------------------------------------------------------


class CctnsMirror:
    """Protocol-ish — both implementations expose ``list_tables`` and ``execute``."""

    def list_tables(self) -> dict[str, list[dict[str, str]]]:  # pragma: no cover - interface
        raise NotImplementedError

    def execute(
        self, sql: str, *, row_cap: int, statement_timeout_ms: int
    ) -> tuple[list[str], list[tuple], int]:  # pragma: no cover - interface
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock mirror — used in dev and in the gate tests
# ---------------------------------------------------------------------------


class MockMirror(CctnsMirror):
    """In-process synthetic CCTNS mirror.

    ≥ 500 FIR rows spread across ≥ 75 districts, ≥ 5 logical tables:
    ``fir``, ``accused``, ``victim``, ``officer``, ``district``.

    The mock implements the SQL subset we actually use in Phase 1 — `SELECT`,
    `WHERE`, `COUNT(*)`, aggregate functions — anything else raises.
    """

    @classmethod
    def seeded(cls) -> "MockMirror":
        return cls(seed=42)

    def __init__(self, *, seed: int = 42) -> None:
        from cctns_analyst.tools.mock_mirror import (
            MOCK_DISTRICTS,
            build_mock_tables,
        )

        self._tables = build_mock_tables(seed=seed)
        self._districts = MOCK_DISTRICTS

    # -- public API -----------------------------------------------------------

    def list_tables(self) -> dict[str, list[dict[str, str]]]:
        out: dict[str, list[dict[str, str]]] = {}
        for name, cols in self._tables.columns_by_table.items():
            out[name] = [{"name": c, "type": _infer_type(c, name)} for c in cols]
        return out

    def execute(
        self, sql: str, *, row_cap: int, statement_timeout_ms: int
    ) -> tuple[list[str], list[tuple], int]:
        # Import lazily so the unit tests don't pull pandas-like deps at collection time.
        from cctns_analyst.tools.mock_mirror import execute_select

        return execute_select(self._tables, sql, row_cap=row_cap)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------


def get_mirror_runner(
    settings=None,
) -> tuple[
    Callable[[str], tuple[list[str], list[tuple], int]],
    Callable[[], dict[str, list[dict[str, str]]]],
]:
    """Return ``(mirror_runner, schema_provider)`` for the configured mode.

    ``mirror_runner`` is the call-sig the graph expects:
    ``mirror_runner(sql) -> (columns, rows, raw_count)``.
    Row cap + statement timeout are taken from settings.
    """
    s = settings or get_settings()
    if (s.cctns_mirror_url or "").strip():
        return _live_runner(s)
    mirror = MockMirror.seeded()
    return _wrap_mock(mirror, s)


def _wrap_mock(
    mirror: MockMirror, s: Any
) -> tuple[
    Callable[[str], tuple[list[str], list[tuple], int]],
    Callable[[], dict[str, list[dict[str, str]]]],
]:
    row_cap = s.row_cap

    def runner(sql: str) -> tuple[list[str], list[tuple], int]:
        # We bound the statement timeout in the mock by simply NOT honouring
        # it (the in-process query is instant for fixtures up to ~10k rows);
        # we still respect ``row_cap`` strictly.
        return mirror.execute(sql, row_cap=row_cap, statement_timeout_ms=s.statement_timeout_ms)

    return runner, mirror.list_tables


def _live_runner(s: Any) -> tuple[Callable, Callable]:
    """Phase 3 placeholder — raises until the live connector ships."""
    raise NotImplementedError(
        "Live CCTNS mirror connector is Phase 3 (per spec/roadmap.md)."
        " Leave CCTNS_MIRROR_URL blank for the dev mock mirror."
    )


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------


_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke)\b", re.I)


def assert_select_only(sql: str) -> None:
    """Reject any DDL/DML — used both inside the mock and the (Phase 3) live path."""
    s = sql.strip().rstrip(";").strip()
    head = s.split(None, 1)[0].lower() if s else ""
    if head != "select":
        raise ValueError(f"only SELECT is allowed; got {head!r}")
    if _FORBIDDEN.search(s):
        raise ValueError("DDL/DML keywords are forbidden in mirror queries")
    # Refuse multiple statements.
    if ";" in s:
        raise ValueError("multiple statements are forbidden")


def _infer_type(column: str, table: str) -> str:
    """Tiny heuristic so the LLM schema dump looks plausible."""
    lc = column.lower()
    if lc.endswith("_at") or lc in {"date", "dob"}:
        return "datetime"
    if lc in {"count", "total", "firs", "accused_count"}:
        return "int"
    return "varchar"
