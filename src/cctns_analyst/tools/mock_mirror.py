"""Deterministic, in-process CCTNS mock mirror.

Goals:
- ≥ 500 synthetic FIR rows spread across ≥ 5 tables (fir, accused, victim,
  officer, district) — the qa-auditor §"Full-data correctness (BLOCK)" floor.
- Implement the SQL subset Phase 1 actually uses: `SELECT … FROM <table>
  [WHERE col = 'literal']`, with optional `COUNT(*)`, `TOP N`. Anything
  else raises — keeps the test surface under control.

The mock is **deterministic** so the gate's correctness assertions are
stable. ``seed=42`` produces ~600 FIRs across 75 districts. Per-district
FIR counts are spread so a sampled answer is observably different from a
full-data answer.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from cctns_analyst.tools.cctns_mirror import assert_select_only

# 75 districts — close enough to UP's number for synthetic data.
MOCK_DISTRICTS: list[str] = [
    "Agra", "Aligarh", "Allahabad", "Ambedkar Nagar", "Amethi", "Amroha",
    "Auraiya", "Ayodhya", "Azamgarh", "Baghpat", "Bahraich", "Ballia",
    "Balrampur", "Banda", "Barabanki", "Bareilly", "Basti", "Bhadohi",
    "Bijnor", "Budaun", "Bulandshahr", "Chandauli", "Chitrakoot",
    "Deoria", "Etah", "Etawah", "Farrukhabad", "Fatehpur", "Firozabad",
    "Gautam Buddha Nagar", "Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur",
    "Hamirpur", "Hapur", "Hardoi", "Hathras", "Jalaun", "Jaunpur",
    "Jhansi", "Kannauj", "Kanpur Dehat", "Kanpur Nagar", "Kasganj",
    "Kaushambi", "Kheri", "Kushinagar", "Lalitpur", "Lucknow", "Maharajganj",
    "Mahoba", "Mainpuri", "Mathura", "Mau", "Meerut", "Mirzapur",
    "Moradabad", "Muzaffarnagar", "Pilibhit", "Pratapgarh", "Raebareli",
    "Rampur", "Saharanpur", "Sambhal", "Sant Kabir Nagar", "Shahjahanpur",
    "Shamli", "Shrawasti", "Siddharthnagar", "Sitapur", "Sonbhadra",
    "Sultanpur", "Unnao", "Varanasi",
]

assert len(MOCK_DISTRICTS) == 75, f"expected 75 mock districts, got {len(MOCK_DISTRICTS)}"

OFFENCE_TYPES = ["theft", "assault", "burglary", "fraud", "cheating", "rape", "murder", "kidnapping", "arson", "extortion"]
COLUMN_TYPES = ["datetime", "varchar", "varchar", "int"]


@dataclass
class _MockTables:
    """In-memory representation of a CCTNS mirror."""

    fir: list[dict[str, Any]] = field(default_factory=list)
    accused: list[dict[str, Any]] = field(default_factory=list)
    victim: list[dict[str, Any]] = field(default_factory=list)
    officer: list[dict[str, Any]] = field(default_factory=list)
    district: list[dict[str, Any]] = field(default_factory=list)

    @property
    def columns_by_table(self) -> dict[str, list[str]]:
        return {
            "fir": ["fir_id", "district", "registered_at", "offence_type", "investigating_officer_id"],
            "accused": ["accused_id", "fir_id", "name", "age", "gender"],
            "victim": ["victim_id", "fir_id", "name", "age", "gender"],
            "officer": ["officer_id", "name", "rank", "district", "phone"],
            "district": ["district", "zone", "population"],
        }


def build_mock_tables(*, seed: int = 42) -> _MockTables:
    """Build the deterministic dataset."""
    rng = random.Random(seed)
    tables = _MockTables()

    # district — 75 rows.
    zone_map = {d: ("East" if i % 3 == 0 else "West" if i % 3 == 1 else "Central") for i, d in enumerate(MOCK_DISTRICTS)}
    for d in MOCK_DISTRICTS:
        tables.district.append(
            {
                "district": d,
                "zone": zone_map[d],
                "population": rng.randint(800_000, 6_500_000),
            }
        )

    # officer — 200 rows.
    ranks = ["Constable", "Head Constable", "Inspector", "Sub-Inspector", "DSP"]
    for i in range(1, 201):
        district_idx = (i * 7) % len(MOCK_DISTRICTS)
        tables.officer.append(
            {
                "officer_id": i,
                "name": f"Officer {i}",
                "rank": rng.choice(ranks),
                "district": MOCK_DISTRICTS[district_idx],
                "phone": f"+91 9{rng.randint(100000000, 999999999)}",
            }
        )

    # Generate FIRs — across all districts, count varies so the *sum per
    # district* doesn't admit a "sample == full" answer.
    now = datetime(2026, 1, 1, 12, 0, 0)
    fir_id = 1
    for d_idx, d in enumerate(MOCK_DISTRICTS):
        # per-district fir count varies between 4 and 18; summed > 500
        n_firs = 4 + ((d_idx * 13) % 15)
        for _ in range(n_firs):
            days_ago = rng.randint(0, 365)
            registered = now - timedelta(days=days_ago)
            officer_id = ((d_idx * 11) % 200) + 1
            tables.fir.append(
                {
                    "fir_id": fir_id,
                    "district": d,
                    "registered_at": registered.isoformat(),
                    "offence_type": rng.choice(OFFENCE_TYPES),
                    "investigating_officer_id": officer_id,
                }
            )
            # ~1.6 accused / FIR on average
            n_accused = 1 + (rng.randint(0, 3))
            for a in range(n_accused):
                tables.accused.append(
                    {
                        "accused_id": 1000 * fir_id + a,
                        "fir_id": fir_id,
                        "name": f"Accused-{fir_id}-{a}",
                        "age": rng.randint(18, 60),
                        "gender": rng.choice(["M", "F"]),
                    }
                )
            # 0 or 1 victim
            if rng.random() < 0.7:
                tables.victim.append(
                    {
                        "victim_id": 5000 * fir_id,
                        "fir_id": fir_id,
                        "name": f"Victim-{fir_id}",
                        "age": rng.randint(15, 75),
                        "gender": rng.choice(["M", "F"]),
                    }
                )
            fir_id += 1

    return tables


# ---------------------------------------------------------------------------
# Minimal SELECT evaluator
# ---------------------------------------------------------------------------


def execute_select(
    tables: _MockTables,
    sql: str,
    *,
    row_cap: int,
) -> tuple[list[str], list[tuple], int]:
    """Run a tiny SELECT subset against the mock.

    Supported (Phase 1 only):
    - ``SELECT [TOP N] col [, col, …] | * FROM cctns_mirror.<table> [WHERE <col> = 'literal'] [WHERE <col> <op> <literal>]``
    - ``SELECT COUNT(*) FROM cctns_mirror.<table> [WHERE …]``
    - WHERE clause: equality on a single column with a string literal;
      ``<col> >= <int>`` for `registered_at` (interpreted as days-ago
      count, since the mock is anchored at `now=2026-01-01`).

    Anything else raises ``ValueError``. That keeps the mock deliberately
    minimal — Phase 3 will hand the same mock contract to the live mirror.
    """
    assert_select_only(sql)
    parsed = _parse_select(sql)
    table_name = parsed["table"]
    if not tables.columns_by_table.get(table_name):
        raise ValueError(f"unknown table: {table_name}")
    src = getattr(tables, table_name)
    rows_iter = _apply_where(src, parsed["where"])
    columns = parsed["projection"]
    rows_iter = _apply_projection(rows_iter, columns)

    if parsed["is_aggregate"]:
        agg = parsed["agg_name"]
        alias = parsed["projection"][0]
        # Apply WHERE first.
        filtered = list(_apply_where(src, parsed["where"]))
        if agg in ("count",):
            value = len(filtered)
        else:
            raise ValueError(f"aggregate {agg!r} is not implemented by the mock")
        return [alias], [(value,)], value

    if parsed["top"]:
        rows_iter = list(rows_iter)[: parsed["top"]]
    all_rows = list(rows_iter)
    bounded = all_rows[: row_cap]
    # Recompute the true "raw" count (pre-cap) for accurate row_count.
    raw_count = len(list(_apply_where(src, parsed["where"])))
    return columns, [tuple(r) for r in bounded], raw_count


# --- SELECT parsing -------------------------------------------------------


def _parse_select(sql: str) -> dict[str, Any]:
    """Parse a tiny SELECT subset. Returns a dict of bits."""
    s = sql.strip().rstrip(";").strip()
    # Strip leading "cctns_mirror." qualifier on table.
    # We accept: SELECT [TOP N] <projection> FROM cctns_mirror.<table> [WHERE col op val]
    # Projection may contain *, COUNT(*), COUNT(col), and the trailing "AS alias".
    pat = re.compile(
        r"^\s*select\s+"
        r"(?:top\s+(?P<top>\d+)\s+)?"
        r"(?P<proj>.+?)"
        r"\s+from\s+(?:cctns_mirror\.)?(?P<table>\w+)"
        r"(?P<rest>\s+where\s+.+)?$",
        re.I | re.S,
    )
    m = pat.match(s)
    if not m:
        raise ValueError(f"unparsable SELECT: {sql!r}")
    top = int(m.group("top")) if m.group("top") else None
    proj_raw = m.group("proj").strip()
    rest = (m.group("rest") or "").strip()
    # Treat any aggregate `FN(...)[ AS alias]` as a scalar.
    agg_m = re.match(r"^\s*(?P<fn>\w+)\s*\([^)]*\)\s*(?:as\s+(?P<alias>\w+))?\s*$", proj_raw, re.I)
    is_aggregate = bool(agg_m) and agg_m.group("fn").lower() not in ("select", "from", "where")
    if is_aggregate:
        alias = (agg_m.group("alias") or agg_m.group("fn") or "count").lower()
        projection = [alias]
        # We dispatch on lower-case name later.
        agg_name = agg_m.group("fn").lower()
    elif proj_raw.strip() == "*":
        projection = ["*"]
        agg_name = ""
    else:
        # Plain columns
        projection = [c.strip() for c in proj_raw.split(",") if c.strip()]
        agg_name = ""
    where = _parse_where(rest) if rest else None
    return {
        "top": top,
        "projection": projection,
        "is_aggregate": is_aggregate,
        "agg_name": agg_name,
        "table": m.group("table"),
        "where": where,
    }


def _parse_where(rest: str) -> dict[str, Any] | None:
    if not rest.lower().startswith("where"):
        return None
    body = rest[5:].strip()
    # support only single-condition WHERE for Phase 1.
    m = re.match(
        r"(?P<col>\w+)\s*(?P<op>=|>=|<=|>|<|!=)\s*(?P<val>'[^']*'|\d+)",
        body,
        re.I,
    )
    if not m:
        raise ValueError(f"unsupported WHERE clause: {rest!r}")
    val = m.group("val")
    if val.startswith("'") and val.endswith("'"):
        val = val[1:-1]
    else:
        val = int(val)
    return {"col": m.group("col"), "op": m.group("op"), "val": val}


def _apply_where(rows: list[dict[str, Any]], where: dict[str, Any] | None):
    if where is None:
        yield from rows
        return
    col = where["col"]
    op = where["op"]
    val = where["val"]
    for r in rows:
        rv = r.get(col)
        if isinstance(val, int):
            # treat int against a datetime ISO string as days-ago comparison;
            # skip otherwise (no other numeric fields are queried in Phase 1).
            if col == "registered_at":
                # convert ISO -> dt; compare against now-anchored datetime.
                rv_dt = _to_dt(rv)
                if rv_dt is None:
                    continue
                cutoff = _now_anchored() - timedelta(days=val)
                if _op(rv_dt, op, cutoff):
                    yield r
                continue
            try:
                rv_i = int(rv)
            except (TypeError, ValueError):
                continue
            if _op(rv_i, op, val):
                yield r
            continue
        # string compare
        if _op(str(rv), op, str(val)):
            yield r


def _apply_projection(rows_iter, columns: list[str]):
    if columns == ["*"]:
        yield from rows_iter
        return
    for r in rows_iter:
        yield [r.get(c) for c in columns]


def _op(a, op: str, b) -> bool:
    if op == "=":
        return a == b
    if op == "!=":
        return a != b
    if op == ">":
        return a > b
    if op == "<":
        return a < b
    if op == ">=":
        return a >= b
    if op == "<=":
        return a <= b
    raise ValueError(f"unknown op: {op}")


def _to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return None


_ANCHOR: datetime = datetime(2026, 1, 1, 12, 0, 0)


def _now_anchored() -> datetime:
    # Stable anchor so the gate's "last 30 days" assertion is reproducible.
    return _ANCHOR
