"""Unit — shrink_row_cap (Phase 3 token-aware row-cap)."""

from __future__ import annotations

import pytest

from mssql_analyst.tools.row_cap import shrink_row_cap


def test_below_high_water_returns_base():
    """Tokens below the high-water mark leave row_cap unchanged."""
    assert shrink_row_cap(base_row_cap=1000, tokens_used=29_999) == 1000


def test_at_or_above_high_water_shrinks():
    """Past the high-water mark, the row cap shrinks by shrink_factor."""
    # default shrink_factor=0.5 → 1000 * 0.5 = 500
    assert shrink_row_cap(base_row_cap=1000, tokens_used=30_000) == 500


def test_floor_blocks_sub_floor_shrink():
    """If shrink would push under the floor, floor wins (default floor=100)."""
    # base=200, factor=0.5 → 100; floor=100 (default), max=100
    assert shrink_row_cap(base_row_cap=200, tokens_used=80_000) == 100


def test_zero_tokens_never_shrinks():
    """Defensive: even with a 0 burn, base_row_cap is returned unchanged."""
    assert shrink_row_cap(base_row_cap=500, tokens_used=0) == 500


def test_negative_tokens_clamps_to_zero():
    """Negative tokens are clamped to 0 (no shrink)."""
    assert shrink_row_cap(base_row_cap=500, tokens_used=-100) == 500


def test_custom_high_water_mark():
    """Custom high_water_mark shrinks only past the user's knob."""
    # Default line: below the (custom) threshold → no shrink; above → shrink.
    assert shrink_row_cap(base_row_cap=1000, tokens_used=2000, high_water_mark=5000) == 1000
    assert shrink_row_cap(base_row_cap=1000, tokens_used=6000, high_water_mark=5000) == 500


def test_passes_through_when_below_threshold():
    """base_row_cap=1 with tokens above threshold: int(1 * 0.5) = 0; floor clamps to 100."""
    # Below the default high_water_mark=30000, so the function returns base=1.
    assert shrink_row_cap(base_row_cap=1, tokens_used=29_999) == 1
