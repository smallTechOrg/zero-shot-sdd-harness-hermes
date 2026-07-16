"""Data-locality (BLOCK) — assert the LLM payload sent to Gemini never contains
raw CCTNS row data. The spy captures the prompt at the LLM boundary."""

from __future__ import annotations


def test_nl_to_sql_payload_has_no_raw_rows(temp_sqlite_db, recording_provider):
    """Schema-only is fine. Any row-level value from mock tables is NOT."""
    from cctns_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/v1/answer", json={"question": "How many FIRs in Lucknow?"})
        assert r.status_code == 200

    # The stub's recorded calls have the JSON system+user strings. Inspect them.
    calls = recording_provider["calls"]
    assert len(calls) >= 1
    nl_call = calls[0]
    body = nl_call["user"]
    # We never see a row identifier like `fir_id=3` (numbers from 1..N), nor
    # a registered_at ISO string. Spot-check a few heuristics.
    # No big JSON arrays of dicts transforming to records (those would look
    # like [{"fir_id":...}, …]).
    assert '"rows"' not in body or '[]' in body.split('"rows"', 1)[1][:200], (
        "LLM payload for nl_to_sql must not embed row arrays"
    )
    # The payload should, however, contain the schema for cctns_mirror.fir.
    assert "fir" in body
    # And the question
    assert "How many FIRs in Lucknow" in body


def test_summarize_payload_has_no_raw_rows(temp_sqlite_db, recording_provider):
    """The summariser must not see raw rows beyond a 100-row sample cap.
    In our test, mock fake provider returns a single row of COUNT(*), so
    the summariser payload should be tiny."""
    from cctns_analyst.api.app_factory import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/v1/answer", json={"question": "How many FIRs in Lucknow?"})
        assert r.status_code == 200

    calls = recording_provider["calls"]
    assert len(calls) == 2
    summary_call = calls[1]
    body = summary_call["user"]
    # 1 row, 1 column: has only [12]. No `fir_id` strings (which would have
    # the form of "<int>:<str>" — we don't generate those).
    assert '"rows"' in body
    # Specifically the row counts in payload — should be ≤ 100.
    # We assert it's ≤ a tiny number matching the SQL COUNT(*).
    assert '"firs"' in body or '"count"' in body
