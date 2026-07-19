"""Unit — validate_sql_structure (Phase 3 retry-loop helper)."""

from __future__ import annotations

import pytest

from mssql_analyst.tools.structural_validator import validate_sql_structure


def test_empty_sql_complains():
    clean, complaints = validate_sql_structure("")
    assert clean is False
    assert any("empty" in c for c in complaints)


def test_select_star_complains():
    clean, complaints = validate_sql_structure("SELECT * FROM INFORMATION_SCHEMA.TABLES")
    assert clean is False
    assert any("unbounded" in c.lower() or "select *" in c.lower() for c in complaints)


def test_select_star_no_where_complains():
    """``SELECT *`` alone (no TOP, no WHERE) flags as unbounded."""
    clean, complaints = validate_sql_structure("SELECT * FROM INFORMATION_SCHEMA.TABLES")
    assert clean is False
    # The complaint contains "unbounded" (covers the "may scan whole table" property).
    assert any("unbounded" in c.lower() for c in complaints)
    # And it should mention either TOP or WHERE so the LLM gets a hint.
    assert any("top" in c.lower() or "where" in c.lower() for c in complaints)


def test_select_columns_no_where_is_clean():
    clean, complaints = validate_sql_structure(
        "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES"
    )
    assert clean is True
    assert complaints == []


def test_select_top_n_is_clean():
    clean, complaints = validate_sql_structure(
        "SELECT TOP 10 * FROM INFORMATION_SCHEMA.TABLES"
    )
    assert clean is True


def test_select_columns_with_where_is_clean():
    clean, complaints = validate_sql_structure(
        "SELECT name FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
    )
    assert clean is True


def test_trailing_semicolon_tolerated():
    clean, complaints = validate_sql_structure(
        "SELECT name FROM INFORMATION_SCHEMA.TABLES;"
    )
    assert clean is True
