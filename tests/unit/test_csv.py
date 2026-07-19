"""Unit tests for the CSV helper (Phase 2)."""

from __future__ import annotations

from mssql_analyst.tools.csv_export import to_csv


def test_header_only():
    assert to_csv(["a", "b"], []) == "a,b\r\n"


def test_simple_row():
    out = to_csv(["a", "b"], [[1, 2], [3, 4]])
    # CRLF terminators
    assert out == "a,b\r\n1,2\r\n3,4\r\n"


def test_comma_in_value_quoted():
    out = to_csv(["name", "value"], [["a,b", 1]])
    assert out == 'name,value\r\n"a,b",1\r\n'


def test_quote_inside_value_escaped():
    out = to_csv(["name"], [['a"b']])
    assert out == 'name\r\n"a""b"\r\n'


def test_newline_inside_value_quoted():
    out = to_csv(["name"], [["line1\nline2"]])
    assert out == 'name\r\n"line1\nline2"\r\n'


def test_none_cell_emits_empty():
    out = to_csv(["a", "b"], [[None, None]])
    assert out == "a,b\r\n,\r\n"


def test_bool_emits_lowercase():
    out = to_csv(["flag"], [[True], [False]])
    assert out == "flag\r\ntrue\r\nfalse\r\n"


def test_complex_types_str_serialized():
    from datetime import datetime, timezone

    ts = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
    out = to_csv(["ts", "v"], [[ts, 5]])
    # Non-strings go through str(...) and are then quote-escaped if needed. The
    # ISO string does not contain commas / quotes / CR / LF, so no quoting.
    assert out == "ts,v\r\n2026-07-19 12:00:00+00:00,5\r\n"
