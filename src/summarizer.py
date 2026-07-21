"""Aggregate uploaded file payloads into one prompt-capable input summary."""
from __future__ import annotations

from typing import Iterable, Sequence


def _sniff_csv(text: str, max_preview_rows: int = 5) -> tuple[list[str], str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    headers = [h.strip().strip('"').strip("'") for h in lines[0].split(",")] if lines else []
    rows = lines[1: max_preview_rows + 1]
    return headers, "\n".join(rows)


def _file_summary(name: str, content: bytes, max_file_chars: int = 120_000) -> str:
    text = content.decode("utf-8", errors="replace")
    headers, preview = _sniff_csv(text)
    meta = f"FILE: {name}\nCOLUMNS: {', '.join(headers)}\n"
    if preview:
        meta += f"HEAD:\n{preview}\n"
    else:
        meta += "HEAD: <empty>\n"
    remaining = max_file_chars - len(meta) - 24
    if remaining > 0 and len(text) > len(meta) + 20:
        meta += "TAIL:\n" + text[-remaining:]
    return meta


def summarize_files(names: Sequence[str], contents: Iterable[bytes]) -> tuple[str, int]:
    items = list(zip(names, contents))
    parts = []
    for n, c in items:
        try:
            parts.append(_file_summary(n, c))
        except Exception as exc:
            parts.append(f"FILE: {n}\nERROR: {exc}\n")
    return "\n\n".join(parts), len(items)
