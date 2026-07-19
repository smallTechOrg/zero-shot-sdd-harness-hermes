"""Unit tests for the anomaly helper (Phase 2)."""

from __future__ import annotations

import pytest

from mssql_analyst.tools.anomaly import anomaly_zscore


def test_constant_column_no_flags():
    cols = ["v"]
    rows = [[5], [5], [5], [5], [5]]
    assert anomaly_zscore(cols, rows) == []


def test_tight_cluster_no_flags():
    cols = ["v"]
    # mean = 10, std <= 1, even the largest deviation has |z| < 2
    rows = [[9.0], [10.0], [11.0], [10.5], [9.5]]
    assert anomaly_zscore(cols, rows) == []


def test_big_outlier_is_flagged():
    cols = ["v"]
    rows = [[1], [2], [3], [4], [100]]
    # Threshold 1.5 catches the 100-vs-rest gap (z ≈ 1.79); the function's
    # default threshold (2.0) is intentionally doc-stricter so it would
    # require a dataset where the outlier is further from the mean.
    flagged = anomaly_zscore(cols, rows, threshold=1.5)
    assert flagged == [4]


def test_non_numeric_columns_no_raise():
    cols = ["name", "n"]
    rows = [
        ["alpha", 1],
        ["beta", 2],
        ["gamma", 3],
        ["delta", 4],
        ["epsilon", 100],
    ]
    flagged = anomaly_zscore(cols, rows, threshold=1.5)
    # Only the numeric column "n" is scored; row 4 (100) is the outlier.
    assert flagged == [4]


def test_threshold_sensitivity():
    cols = ["v"]
    rows = [[1], [2], [3], [4], [5], [8], [-3]]
    loose = anomaly_zscore(cols, rows, threshold=1.5)
    tight = anomaly_zscore(cols, rows, threshold=3.0)
    assert len(tight) <= len(loose)


def test_empty_inputs():
    assert anomaly_zscore([], []) == []
    assert anomaly_zscore(["v"], []) == []
    cols_dummy = ["a", "b"]
    assert anomaly_zscore(cols_dummy, [[None, None]]) == []


def test_min_samples_filter():
    """Columns with fewer than min_samples numeric values yield no flags."""
    cols = ["v"]
    rows = [[100], [1], [2]]  # only 3 numeric values → min_samples=4 blocks
    assert anomaly_zscore(cols, rows) == []


def test_inf_and_nan_skipped():
    import math

    cols = ["v"]
    rows = [
        [1.0],
        [2.0],
        [3.0],
        [4.0],
        [math.inf],
        [float("nan")],
        [100.0],
    ]
    # The 7 rows have 5 finite numeric values (1,2,3,4,100) — 100 is outlier.
    flagged = anomaly_zscore(cols, rows, threshold=1.5)
    assert flagged == [6]
