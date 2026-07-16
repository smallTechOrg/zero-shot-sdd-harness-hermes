"""Bounded-query test — row_cap is enforced even when the SQL would return more."""

from __future__ import annotations

import json


def test_row_cap_enforced_on_large_result(temp_sqlite_db, monkeypatch):
    """The mock mirror has ~600 FIRs. A SELECT * with no WHERE returns ~600
    rows. The executor must trim to row_cap=10 (we set this on the run)."""

    from cctns_analyst.tools.mock_mirror import build_mock_tables, execute_select

    tables = build_mock_tables(seed=42)
    cols, rows, raw_count = execute_select(
        tables,
        "SELECT fir_id, district FROM cctns_mirror.fir",
        row_cap=10,
    )
    assert raw_count > 10, "fixture should exceed row_cap"
    assert len(rows) == 10, "row_cap must be enforced server-side"


def test_runner_function_signature_enforces_cap(temp_sqlite_db, monkeypatch):
    """`mirror_runner` returned by get_mirror_runner must respect settings.row_cap."""
    from cctns_analyst.api.app_factory import create_app
    from cctns_analyst.tools.cctns_mirror import get_mirror_runner
    from cctns_analyst.config.settings import get_settings

    s = get_settings()
    runner, _schema = get_mirror_runner(s)
    # Set cap low and run; assert cap is observed.
    monkeypatch.setattr(s, "row_cap", 5)
    # Note: we monkeypatched the *instance* not the cached dict above;
    # because settings is a Pydantic model, copy with replace:
    from cctns_analyst.config.settings import Settings
    new_s = s.model_copy(update={"row_cap": 5})
    runner2, _ = get_mirror_runner(new_s)
    cols, rows, raw = runner2("SELECT fir_id FROM cctns_mirror.fir")
    assert raw > 5
    assert len(rows) == 5
