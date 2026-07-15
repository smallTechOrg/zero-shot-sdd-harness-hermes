# Capability: Aggregate & Funnel

## What It Does

Pulls every configured source for the `#local` entity through one connector interface, normalizes the raw signals into a unified event model, computes the blended acquisition+retention funnel and KPI set, and persists a cached snapshot plus a time-series point.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| `entity` | str | request (`#local`) | yes |
| source credentials | env vars | `.env` | no (sample adapter default) |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| `Snapshot` | DB row | SQLite (`snapshots`) |
| `FunnelPoint` | DB row | SQLite (`funnel_points`) — time-series |
| `SourceRecord` | DB row | SQLite (`source_records`) — raw audit trail |
| funnel + kpis JSON | HTTP | `GET /api/funnel`, `/api/kpis` |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Sample adapter | generate synthetic records | n/a (always succeeds) |
| GA4 / DB / Play / App Store / social | `pull()` (Phase 2+) | per-connector: return "not configured", excluded from aggregate; pipeline continues |

## Business Rules

- Funnel stages are fixed: `visit_or_install → signup → activated → retained → revenue`.
- Counts are **blended** web + app.
- If a real connector has no key, it is skipped and the funnel is computed from the remaining sources; the connector is reported `NOT CONFIGURED`.
- In sample mode (no keys), the sample adapter provides all stages so the UI is fully populated. Sample data is labelled `sample: true` in the API response and on the dashboard.

## Success Criteria

- [ ] `GET /api/funnel` returns the 5 stages with non-zero counts and `sample` flag matching data source
- [ ] Each stage count is monotonically non-increasing down the funnel (visit ≥ signup ≥ activated ≥ retained ≥ revenue)
- [ ] `GET /api/snapshots` returns ≥1 point; a Refresh appends a new `FunnelPoint`
- [ ] A DB row exists per pulled source in `source_records` (audit trail)

## Connector State & Setup Guide

- `GET /api/connectors` returns one entry per source family with `configured: bool` and the env var name.
- `GET /api/setup_guide?source=<id>` returns ordered steps (where to get the key, the exact env var, a paste-ready line). No secrets returned.
- UI: each connector card shows CONNECTED / NOT CONFIGURED and a "Set up" button opening the guide.

## Success Criteria (setup guide)

- [ ] Every source family appears in `/api/connectors`
- [ ] A NOT CONFIGURED source returns a non-empty, actionable guide

## Live Dashboard

- `GET /api/kpis` returns signups, activated, retention_pct, revenue.
- Funnel chart (5 bars), KPI tiles, a sparkline of `FunnelPoint` revenue/signups over time, and an insight panel.
- Insight panel: real LLM summary when `AGENT_OPENROUTER_API_KEY` is set; otherwise a clearly-labelled sample insight.
- Refresh button → `POST /api/refresh` → re-runs pipeline → updates all views.

## Success Criteria (dashboard)

- [ ] Dashboard renders funnel + KPIs + sparkline on first load (sample data) with 0 console errors
- [ ] Refresh updates the funnel counts and appends a sparkline point
- [ ] Insight panel is visibly labelled "sample" when no key is set
