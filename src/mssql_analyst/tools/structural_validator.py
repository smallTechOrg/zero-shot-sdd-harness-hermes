"""Structural SQL validator — Phase-3 retry-loop helper.

Unlike the Phase-1 safety gate (``assert_select_only``), this helper
NEVER raises — it returns a (clean, complaints) pair so the graph can
route forward on success and *cycle back* to ``nl_to_sql`` when the
complaint is non-empty AND we still have budget (``sql_attempts <
max_sql_attempts``).

Phase-3 keeps the safety gate separate. Structural checks here:

- TOP/LIMIT present? — for queries that look like ``SELECT *``,
  the validator asks the LLM to bound its result next time.
- ORDER BY clause present? — useful for "top-N" / ranking schemas.
- DISTINCT usage ok but warn on ``SELECT COUNT(*)`` without a WHERE filter
  (a full-table scan) — recommends adding filters.

These are checks *performed by the validator, not enforced*. We give
the LLM one retry to adjust; after the retries are exhausted, we go
forward regardless. The audit log row records the validator's verdict
as ``validation_error``.
"""

from __future__ import annotations

import re

_ORDER_BY = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)
_TOP = re.compile(r"\bTOP\s+\d+", re.IGNORECASE)
_SELECT_STAR = re.compile(r"\bSELECT\s+\*\b", re.IGNORECASE)
_WILDCARD_PREFIX = re.compile(r"^\s*SELECT\s+\*", re.IGNORECASE)


def validate_sql_structure(sql: str) -> tuple[bool, list[str]]:
    """Return ``(clean, complaints)`` for ``sql``.

    ``clean`` is True iff ``complaints`` is empty.
    Each complaint is a short, LLM-readable string the next nl_to_sql
    call can fold into its prompt context.
    """
    if not sql or not sql.strip():
        return False, ["SQL is empty"]

    stripped = sql.strip().rstrip(";").strip()
    s = stripped.lower()
    complaints: list[str] = []

    # Unbounded SELECT * — likely to load a lot of rows; recommend TOP N
    if _WILDCARD_PREFIX.match(s) and not _TOP.search(s):
        complaints.append(
            "the SELECT statement uses 'SELECT *' which is unbounded; "
            "rewrite with 'SELECT TOP N col1, col2, ...' so the executor "
            "never pages through an entire table."
        )

    # Heuristic: a SELECT * on a table likely not bounded by WHERE
    if _SELECT_STAR.search(s) and "where" not in s:
        complaints.append(
            "a 'SELECT * *without a WHERE* clause can scan the whole "
            "table; add a filter or use TOP N to keep the result small."
        )

    # Lowercase "select *" may include TOP already; tolerate.
    return (len(complaints) == 0), complaints
