"""MSSQL schema introspection and caching.

This module provides a function to get the database schema (tables and columns)
and cache it for use by the LLM agent. The schema is retrieved via SQLAlchemy
inspection and returned as a dictionary suitable for inclusion in LLM prompts.
"""
from __future__ import annotations

from threading import Lock
from typing import Dict, List

from sqlalchemy import inspect

from src.db.session import get_engine

# Global cache for the schema
_schema_cache: Dict[str, List[dict]] | None = None
_schema_lock = Lock()


def get_schema() -> Dict[str, List[dict]]:
    """Return the database schema as a dict of table name to list of columns.

    Each column is represented as a dict with keys "name" and "type".

    The result is cached on first call; subsequent calls return the same dict.
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    with _schema_lock:
        # Double-check locking
        if _schema_cache is not None:
            return _schema_cache

        engine = get_engine()
        inspector = inspect(engine)
        schema: Dict[str, List[dict]] = {}

        for table_name in inspector.get_table_names():
            # Skip system tables if desired, but we keep all for now.
            columns = []
            for column in inspector.get_columns(table_name):
                # We only need the name and type for the LLM context.
                columns.append(
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                    }
                )
            schema[table_name] = columns

        _schema_cache = schema
        return schema


def clear_schema_cache() -> None:
    """Clear the cached schema. Primarily useful for testing."""
    global _schema_cache
    _schema_cache = None