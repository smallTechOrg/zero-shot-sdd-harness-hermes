"""SQL safety validator — enforces \"read-only\" at the SQL layer.

Phase 1 schema is intentionally minimal:

- Statement MUST start with ``SELECT`` or ``WITH``.
- A semicolon (;) inside the statement means more than one statement; we
  refuse anything that contains ``;`` after the trailing whitespace strip.
- We refuse any keyword in the DDL/DML set (case-insensitive):
  INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE,
  EXEC, EXECUTE.

This runs both before the LLM call (in the prompt, as a hard rule) AND
after (in the graph node, where rejection becomes ``error: \"unsafe_sql\"``).
"""

from __future__ import annotations

import re

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|exec(ute)?)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """Raised when a SQL string fails the read-only validator."""


def assert_select_only(sql: str) -> None:
    """Raise ``UnsafeSQLError`` if ``sql`` is not a single read-only SELECT.

    The rule is intentionally strict — we are happy to reject valid reads
    if they look unsafe (e.g. a CTE that joins on a CTE-named ``update``).
    Callers should fall back to a more constrained query.
    """
    if not sql or not sql.strip():
        raise UnsafeSQLError("empty SQL")
    s = sql.strip().rstrip(";").strip()
    head = s.split(None, 1)[0].lower() if s else ""
    if head not in {"select", "with"}:
        raise UnsafeSQLError(f"only SELECT/WITH is allowed; got {head!r}")
    if _FORBIDDEN.search(s):
        raise UnsafeSQLError(
            "DDL/DML keywords are forbidden in mirror queries"
        )
    # Refuse multiple statements: the only allowed semicolon is the trailing one,
    # which we just stripped. Any remaining ``;`` means more than one statement.
    if ";" in s:
        raise UnsafeSQLError("multiple statements are forbidden")
