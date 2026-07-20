"""Test the MSSQL schema introspection and caching."""
from __future__ import annotations

import pytest

from src.db.mssql.schema import clear_schema_cache, get_schema


def test_get_schema_returns_dict(mssql_db: str):
    """get_schema should return a dictionary of tables and columns."""
    schema = get_schema()
    assert isinstance(schema, dict)
    # We expect at least the audit table to be present after migrations
    assert "audit_log" in schema
    # Each table should have a list of columns, each with name and type
    for table_name, columns in schema.items():
        assert isinstance(columns, list)
        for col in columns:
            assert "name" in col and isinstance(col["name"], str)
            assert "type" in col and isinstance(col["type"], str)


def test_get_schema_is_cached(mssql_db: str):
    """Calling get_schema twice should return the same object."""
    schema1 = get_schema()
    schema2 = get_schema()
    assert schema1 is schema2  # same object due to caching


def test_clear_schema_cache(mssql_db: str):
    """clear_schema_cache should reset the cache."""
    schema1 = get_schema()
    clear_schema_cache()
    schema2 = get_schema()
    # After clearing, we should get a new dictionary (same content, but different object)
    assert schema1 is not schema2
    assert schema1 == schema2  # content should be the same