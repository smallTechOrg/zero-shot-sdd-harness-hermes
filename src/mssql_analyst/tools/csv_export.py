"""CSV serializer for the bounded SELECT result.

Pure function — no I/O. Called by the `/api/ask/{run_id}/csv` endpoint.

Quote-escaping: RFC 4180-style — wrap a value in double quotes if it
contains a comma, double-quote, CR, or LF; escape inner double quotes by
doubling them. Strings are emitted as-is; numbers as their natural repr;
None as the empty string (matches what most CSV consumers expect).
"""

from __future__ import annotations

from typing import Any


def _escape(cell: str) -> str:
    if any(ch in cell for ch in (",", '"', "\n", "\r")):
        return '"' + cell.replace('"', '""') + '"'
    return cell


def to_csv(
    columns: list[str],
    rows: list[list[Any]],
) -> str:
    """Serialize ``columns`` + ``rows`` to a single CSV string.

    Always emits a header row (even when ``rows`` is empty). Uses CRLF as
    the line terminator (RFC 4180) so Excel-friendly.
    """
    out_lines = [",".join(_escape(c) for c in columns)]
    for row in rows:
        cells: list[str] = []
        for v in row:
            if v is None:
                cells.append("")
            elif isinstance(v, bool):
                cells.append("true" if v else "false")
            elif isinstance(v, (int, float)):
                cells.append(repr(v))
            else:
                cells.append(_escape(str(v)))
        out_lines.append(",".join(cells))
    # RFC 4180 line terminator.
    return "\r\n".join(out_lines) + "\r\n"
