"""Unit tests for the mock CCTNS mirror — qa-auditor §"Full-data correctness (BLOCK)" floor."""

from __future__ import annotations

from cctns_analyst.tools.mock_mirror import (
    MOCK_DISTRICTS,
    build_mock_tables,
    execute_select,
)


def test_at_least_500_firs():
    tables = build_mock_tables(seed=42)
    assert len(tables.fir) >= 500, (
        f"qa-auditor floor: >= 500 FIRs (got {len(tables.fir)}); "
        "sample-vs-full correctness test would not differentiate."
    )


def test_at_least_5_distinct_tables():
    tables = build_mock_tables(seed=42)
    nonempty_tables = sum(
        1 for name in ("fir", "accused", "victim", "officer", "district")
        if len(getattr(tables, name)) > 0
    )
    assert nonempty_tables >= 5, (
        f"qa-auditor floor: >= 5 distinct tables with rows (got {nonempty_tables})"
    )


def test_districts_at_least_75():
    assert len(MOCK_DISTRICTS) >= 75  # close to UP's 75 districts


def test_count_returns_full_dataset_number():
    """Sum of per-district FIR counts (the SQL would compute) equals the full count."""
    tables = build_mock_tables(seed=42)
    cols, rows, raw_count = execute_select(
        tables,
        "SELECT COUNT(*) AS firs FROM cctns_mirror.fir",
        row_cap=1000,
    )
    assert cols == ["firs"]
    assert rows == [(len(tables.fir),)]
    assert raw_count == len(tables.fir)


def test_per_district_filter_is_bounded_by_full_data():
    """A per-district WHERE returns per-district counts that vary — proving
    that sampling would diverge from full data."""
    tables = build_mock_tables(seed=42)
    cols, rows, raw_count = execute_select(
        tables,
        "SELECT COUNT(*) AS firs FROM cctns_mirror.fir WHERE district = 'Lucknow'",
        row_cap=1000,
    )
    # The number of FIRs in Lucknow is determined by the build function —
    # it's NOT the full count and not zero. We assert it's >0 and not equal
    # to the full count.
    assert raw_count > 0
    assert raw_count < len(tables.fir), (
        "per-district count must be less than full count; "
        "if you see this fail, the mock fixture is degenerating."
    )


def test_list_tables_payload_has_columns_but_no_rows():
    """The schema dump (sent to the LLM) must list columns but contain no row data."""
    from cctns_analyst.tools.cctns_mirror import MockMirror

    m = MockMirror.seeded()
    schema = m.list_tables()
    assert "fir" in schema
    for col in schema["fir"]:
        assert "name" in col and "type" in col
    # No raw row leaks: the schema payload must be a plain dict-of-lists, no values.
    for table, cols in schema.items():
        for c in cols:
            for k, v in c.items():
                assert isinstance(v, str), f"{table}.{k} must be a column attribute (str), got {type(v)}"
    # We deliberately do not assert anything else about the columns — the
    # prompt-spy test (integration) inspects the LLM payload directly.


def test_assert_select_only_rejects_ddl():
    from cctns_analyst.tools.cctns_mirror import assert_select_only

    for bad in (
        "INSERT INTO cctns_mirror.fir VALUES (1)",
        "UPDATE cctns_mirror.fir SET x=1",
        "DELETE FROM cctns_mirror.fir",
        "DROP TABLE cctns_mirror.fir",
        "ALTER TABLE cctns_mirror.fir ADD COLUMN x int",
    ):
        try:
            assert_select_only(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected DDL rejection for: {bad!r}")


def test_assert_select_only_rejects_multi_statement():
    from cctns_analyst.tools.cctns_mirror import assert_select_only

    try:
        assert_select_only("SELECT 1 FROM cctns_mirror.fir; SELECT 2 FROM cctns_mirror.fir")
    except ValueError:
        return
    raise AssertionError("expected multi-statement rejection")
