"""Anomaly detection helper.

Pure function — no I/O, no DB. Called by the `/api/ask/{run_id}/anomalies`
endpoint, post-loaded from `answer_runs.result_rows_json`.

The heuristic: for each numeric column, compute mean + std-dev across all
non-null cells; flag rows whose absolute z-score is >= `threshold`. If the
column has fewer than `min_samples` numeric values we return no flags for
that column. Constant columns (std-dev == 0) yield no flags.
"""

from __future__ import annotations

import math
from typing import Any


def _is_real_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not (
        isinstance(v, float) and (math.isnan(v) or math.isinf(v))
    )


def anomaly_zscore(
    columns: list[str],
    rows: list[list[Any]],
    *,
    threshold: float = 2.0,
    min_samples: int = 4,
) -> list[int]:
    """Return the list of unique zero-based row indices flagged as anomalies.

    A row is flagged if its value in **any** numeric column has |z| >= threshold.

    ``columns`` is the projection list; ``rows`` is the data. Empty rows
    returns ``[]`` rather than raising.
    """
    if not rows or not columns:
        return []
    n_rows = len(rows)
    flagged: set[int] = set()
    n_cols = len(columns)
    for col_idx in range(n_cols):
        col_vals: list[float] = []
        col_row_idx: list[int] = []
        for row_idx, row in enumerate(rows):
            v = row[col_idx] if col_idx < len(row) else None
            if _is_real_number(v):
                col_vals.append(float(v))
                col_row_idx.append(row_idx)
        if len(col_vals) < min_samples:
            continue
        mean = sum(col_vals) / len(col_vals)
        # Sample variance (Bessel-corrected, / (n - 1)) — standard for z-scores.
        # Avoids the boundary-case loss of one degree of freedom and keeps
        # the math stable for small samples.
        if len(col_vals) < 2:
            continue
        variance = sum((x - mean) ** 2 for x in col_vals) / (len(col_vals) - 1)
        std = math.sqrt(variance)
        if std == 0:
            continue
        for v, row_idx in zip(col_vals, col_row_idx):
            z = (v - mean) / std
            if abs(z) >= threshold:
                flagged.add(row_idx)
    return sorted(flagged)
