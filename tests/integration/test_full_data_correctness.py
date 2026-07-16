"""Full-data correctness gate — qa-auditor §"Full-data correctness (BLOCK)".

The fixture is large enough that sample != full, and the test asserts the
computed value the agent would return, not a count proxy.
"""

from __future__ import annotations


def test_full_data_count_matches_fixture(temp_sqlite_db):
    """SELECT COUNT(*) FROM cctns_mirror.fir returns the number of FIRs in the
    full fixture (≥ 500)."""
    from cctns_analyst.tools.mock_mirror import build_mock_tables, execute_select

    tables = build_mock_tables(seed=42)
    cols, rows, raw_count = execute_select(
        tables,
        "SELECT COUNT(*) AS total FROM cctns_mirror.fir",
        row_cap=1000,
    )
    assert raw_count >= 500, (
        "fixture must be ≥ 500 to differentiate sample vs full"
    )
    assert rows == [(raw_count,)], "the value must be exactly the full count, not a sample"


def test_per_district_sum_equals_total(temp_sqlite_db):
    """Sum of per-district counts equals the full total — sanity check that
    the fixtures form a coherent dataset."""
    from cctns_analyst.tools.mock_mirror import build_mock_tables, execute_select

    tables = build_mock_tables(seed=42)
    cols, rows, raw_count = execute_select(
        tables,
        "SELECT COUNT(*) AS total FROM cctns_mirror.fir",
        row_cap=1000,
    )
    total = rows[0][0]

    districts = sorted({r["district"] for r in tables.district})
    run_total = 0
    for d in districts:
        _, _, district_count = execute_select(
            tables,
            f"SELECT COUNT(*) AS n FROM cctns_mirror.fir WHERE district = '{d}'",
            row_cap=1000,
        )
        run_total += district_count

    # Every FIR belongs to exactly one district; the totals must match.
    assert run_total == total, (
        f"district-sum {run_total} != total {total} — fixture drift; "
        "the gate cannot trust this dataset for full-data answers."
    )
