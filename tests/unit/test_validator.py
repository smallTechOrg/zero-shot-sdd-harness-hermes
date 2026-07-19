"""Unit tests — read-only SQL validator."""

from __future__ import annotations

import pytest

from mssql_analyst.tools.validator import UnsafeSQLError, assert_select_only


SAFE = [
    "SELECT TOP 10 * FROM INFORMATION_SCHEMA.TABLES",
    "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES",
    "WITH c AS (SELECT 1 AS x) SELECT c.x FROM c",
    "select id from dbo.users",
    "  SELECT * FROM foo  ",
]

UNSAFE = [
    "DROP TABLE foo",
    "INSERT INTO foo VALUES (1)",
    "UPDATE foo SET x=1",
    "DELETE FROM foo",
    "CREATE TABLE foo (x INT)",
    "ALTER TABLE foo ADD x INT",
    "TRUNCATE TABLE foo",
    "GRANT SELECT ON foo TO bar",
    "REVOKE SELECT ON foo FROM bar",
    "EXEC sp_something",
    "EXECUTE sp_something",
    "SELECT 1; DROP TABLE foo",
    "SELECT 1; SELECT 2",
    "",
    "   ",
    "WITH c AS (DELETE FROM foo RETURNING id) SELECT id FROM c",
]


@pytest.mark.parametrize("sql", SAFE)
def test_safe_sql_passes(sql):
    assert_select_only(sql)  # does not raise


@pytest.mark.parametrize("sql", UNSAFE)
def test_unsafe_sql_is_rejected(sql):
    with pytest.raises(UnsafeSQLError):
        assert_select_only(sql)
