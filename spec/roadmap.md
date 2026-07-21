# Roadmap

> **UP Police Data Analyst Agent** — spec-manifest-complete. Assumed flags are listed in the return summary; no `<!-- FILL IN -->` remain.

---

## What This Agent Does

UP Police Data Analyst Agent lets personnel upload one or more CSV datasets (crime incidents, FIR exports, district statistics, calls-for-service) and ask questions in plain Hindi or English. The agent converts questions into SQL or Python, executes them safely against the data, and returns a natural-language answer alongside the generated code, result tables, and optional charts or downloadable reports. Phase 2 extends the same experience to a large MsSQL database with query caching and aggregation so response latency stays low and the production database feels no extra load.

## Who Uses It

- Investigation officers (IO) — case-level queries, trend checks, data-backed reasoning
- Senior officers (SP/DCP) — month/quarter reviews, hotspot summaries, drill-downs
- Data cell / analyst teams — ad-hoc deep dives, multi-file merges, report generation
- Field personnel — browser-only access, no terminal required

## Core Problem Being Solved

Forces manually export CSVs or run direct DB queries, copy-paste into Excel or Python notebooks, and stitch answers together by hand. There is no single, auditable, on-prem interface that accepts natural-language questions across multiple datasets and produces code-transparent, shareable outputs. MsSQL access is risky: ad-hoc queries from analysts run full-table scans and spike production load.

## Success Criteria

- [ ] A user uploads 3 CSV files and gets a correct natural-language answer to a complex multi-table question in under 30 seconds (Phase 1)
- [ ] The generated SQL/Python code is shown alongside every answer and matches the returned result
- [ ] The same agent connects to MsSQL using the existing driver/credentials and answers live-DB questions with ≤5s p95 latency (Phase 2)
- [ ] Query caching reduces repeated identical DB hits by ≥80% on hotspot patterns
- [ ] Audit trail captures: user, question, generated SQL, result row count, latency, and success/failure

## What This Agent Does NOT Do (Out of Scope)

- Write or modify data in any datasource (read-only)
- Access the internet or external cloud services for inference (on-prem only)
- Handle biometric / video / unstructured-media files
- Replace MIS dashboards — it is a complement for ad-hoc analytical queries
- Enforce UP Police policy decisions (advisory only)

## Key Constraints

- **Security:** All data must remain on-prem at all times. No row leaves the data server. LLM inference is served from an on-prem/air-gapped endpoint.
- **Cost:** Prefer open-source or low-cost LLM option; infrastructure runs on existing police hardware.
- **Latency:** Phase 2 p95 ≤ 5s against live MsSQL; Phase 1 target ≤ 15s on 1–10 lakh row CSVs.
- **DB load:** Phase 2 must use query caching, result deduplication, and read-only routing so production load is indistinguishable from baseline.
- **Reliability:** Production-grade from Day 1 — crash recovery, role-based access control, full audit log.
- **Port:** Development server uses port configured in `src/config/settings.py` (default 8001).

---

## Phases of Development

### Phase 1 — CSV Query *(smallest user-testable win)*

**Goal:** Upload CSVs → ask questions in natural language → get answers + code + tables, end-to-end, real on the tested path.

**Independent slices (parallel build units):**
- `slice-a` (backend) — CSV ingestion, schema inference, SQLite-backed storage, LangGraph query pipeline, SQL generation & execution — deps: none
- `slice-b` (backend) — Observability + audit trail + model + session persistence — deps: none
- `slice-c` (frontend) — Zero-build static upload UI + chat + code display — deps: none

**Key surfaces / files:**
- `src/graph/nodes.py` — adds `csv_query` node (extends baseline `transform_text` slot in-place)
- `src/prompts/csv-query.md` — system prompt for CSV/SQL generation
- `src/domain/models.py` — uploaded dataset model + session history
- `src/api/routes.py` — POST `/upload`, POST `/query`, GET `/datasets`
- `frontend/public/` — `index.html`, `app.js`, `styles.css` (upload drag-drop + chat)
- `src/observability/audit.py` — structured audit logger

**Gate:** `uv run pytest tests/integration/test_phase1_csv_query.py -q`
> Real primary LLM key from `.env`, real SQLite DB — no SQLite stub mode.

**How the user tests it (handoff seed):**
1. Run `.venv/bin/python -m src` (root owns the server; user does not run commands)
2. Open the ONE live URL (port logged at startup)
3. Upload 2 sample CSVs (FIR + district stats) via drag-drop
4. Type: "Show me district-wise total FIR count for 2024"
5. Expected: NL answer + generated SQL shown in code block + result table rendered. No rough edges.
6. Labelled stubs shown: MsSQL connection, Charts, Reports (clearly greyed out / "coming in Phase 2")

---

### Phase 2 — MsSQL + Charts + Reports

**Goal:** Connect to a live MsSQL database with the same natural-language experience, plus chart generation and downloadable PDF/Excel reports.

**Independent slices (parallel build units):**
- `slice-a` (backend) — pyodbc MsSQL adapter, schema introspection, read-only query execution, aggregation cache layer — deps: slice-a of Phase 1
- `slice-b` (backend) — Chart generation tool (matplotlib → PNG/SVG) + Report tool (PDF/Excel via reportlab/openpyxl) — deps: none
- `slice-c` (frontend) — Charts, tables, report download buttons — deps: none

**Key surfaces / files:**
- `src/config/settings.py` — adds MSSQL_URL, MSSQL_CACHE_TTL, CACHE_BACKEND
- `src/db/mssql.py` — pyodbc connection pool + read-only enforcement
- `src/db/cache.py` — in-memory or Redis-backed query cache
- `src/llm/tools/chart_tool.py` — matplotlib-based chart generator, returns base64 PNG
- `src/llm/tools/report_tool.py` — PDF + Excel generator
- `src/prompts/csv-query.md` — updated to support MsSQL datasource
- `frontend/public/` — adds chart rendering, report download buttons

**Gate:** `uv run pytest tests/integration/test_phase2_mssql_reporting.py -q`
> Real primary LLM key from `.env`, real pyodbc driver against a test MsSQL instance.

**How the user tests it (handoff seed):**
1. Same server running (root-owned), same URL
2. Navigate to MsSQL tab (now live)
3. Enter MsSQL connection details → connect
4. Type: "Top 5 districts by crime count last month"
5. Expected: NL answer + generated SQL + chart + table. Download PDF/Excel buttons work.
6. Re-run the same query twice → second response from cache (audit log shows cache hit).
