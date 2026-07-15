# UI

Single screen served at `http://localhost:8001/app/`. Next.js 15 static export, `basePath: '/app'`. Calls only `/api/*`.

## Screens / components

1. **Header** — `#local Analytics`, entity pill, Refresh button (top-right).
2. **Funnel panel** — 5 horizontal/vertical bars: Visit/Install → Signup → Activated → Retained → Revenue, each with count + % of top. A `SAMPLE DATA` badge when `sample: true`.
3. **KPI tiles** — Signups, Activated, Retention %, Revenue (from `/api/kpis`).
4. **Trend sparkline** — revenue (or signups) over `FunnelPoint`s from `/api/snapshots`.
5. **Connectors panel** — 6 cards (GA4, Business DB, Play, App Store, Instagram, LinkedIn, Facebook). Each shows CONNECTED (green) or NOT CONFIGURED (amber) + a "Set up" button.
6. **Connector setup modal** — opened by "Set up"; shows ordered steps from `/api/setup_guide`. Clearly labelled: "Phase 2 will make this live."
7. **Insight panel** — plain-language summary; labelled "sample" when no key.
8. **Stub chips (clearly labelled)** — Notifications (🔔 "Phase 2"), Scheduled refresh (⏱ "Phase 2"), Real connectors (badge on each card).

## Interactions

- On load: `GET /api/funnel`, `/api/kpis`, `/api/snapshots`, `/api/connectors` in parallel; render.
- Refresh: `POST /api/refresh` → refetch all → update funnel/KPIs/sparkline; show toast "Updated".
- Set up (connector): open modal with guide.

## States (every surface)

- **Empty:** first load before any snapshot → show sample funnel (sample adapter guarantees data).
- **Loading:** skeletons while fetching.
- **Error:** API error → inline message + Retry, never a stack trace.

## Stubs (must be visibly labelled, never look like bugs)

- Notifications bell, scheduled-refresh toggle, and the six real connectors are all labelled "Phase 2 / not configured yet".
