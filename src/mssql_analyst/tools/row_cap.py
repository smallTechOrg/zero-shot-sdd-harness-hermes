"""Token-aware row-cap computation.

Used by the Phase-3 ``execute_sql`` node so that runs which have already
spent a lot of Gemini tokens (e.g. multi-attempt retries) clamp tighter
than the configured per-row cap, keeping the bounded SELECT footprint
predictable under load.
"""

from __future__ import annotations


def shrink_row_cap(
    *,
    base_row_cap: int,
    tokens_used: int,
    high_water_mark: int = 30_000,
    shrink_factor: float = 0.5,
    floor: int = 100,
) -> int:
    """Return the row-cap to clamp the next SELECT with.

    Behaviour:
    - If ``tokens_used < high_water_mark``: returns ``base_row_cap`` unchanged.
    - Otherwise, returns the floor of ``base_row_cap * shrink_factor``
      with a lower bound of ``floor``. The metric is a linear reduction in
      relation to how far past the high-water mark the run is; we keep it
      simple: just halve once past the threshold and clamp at ``floor``.

    Pure function. ``base_row_cap`` must be > 0; the floor clamps the result.
    """
    base = max(1, int(base_row_cap))
    tokens = max(0, int(tokens_used))
    if tokens < max(0, int(high_water_mark)):
        return base
    return max(int(floor), int(base * float(shrink_factor)))
