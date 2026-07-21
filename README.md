# CrimAnalyze — UP Police Data Analyst Agent

Give it multiple CSV datasets and an investigator question. Walk away with a grounded insight summary and a chart spec.

A **data analyst agent** built for the UP Police on the **zero-shot harness** (FastAPI + LangGraph + SQLite, provider-agnostic LLM). Phase 1 supports **multi-file CSV upload** and **natural-language Q&A**; Phase 2 adds a **read-only MsSQL federation layer** with query caching to reduce live-DB load and improve latency.

---

## The Spirit

1. **Spec is the source of truth.** Written before the code, always. When spec and code disagree, the spec wins (`/zero-shot-sync`).
2. **Built for two audiences at once.** A police analyst drives it with files + one question; a senior engineer inherits a clean FastAPI + LangGraph stack they can read, review, and own.
3. **Lean harness, not a framework.** `harness/` is engineering *mindfulness* — rules and patterns that keep every session consistent. The product runtime stays provider-agnostic.
4. **Smallest first-time-right win, phase by phase.** Each phase ships the smallest increment a human can actually test, and it must work the *first* time they test it.
5. **A human gates every phase.** Autonomous *within* a phase; stops at each boundary for you to test the increment.
6. **Real LLM/API or it doesn't count.** Gates and tests run against the real model with keys from `.env`. A stubbed pass is not a pass.

---

## What This Is

- A working **data analyst agent** in `src/` — FastAPI + LangGraph + SQLite, provider-agnostic
  LLM (`analyze_data` capability), structured logging, graceful error paths. **Tests pass out of the box.**
- A **zero-build static frontend** in `frontend/public/` served by the backend at `/app` — multi-file
  CSV upload + question form.
- A **filled spec** in `spec/` — roadmap, architecture, capabilities, data, api, ui, and
  the agent graph for multi-CSV analysis.
- A **Phase 2 plan** for MsSQL federation + query cache.
- Three **skills**: `/zero-shot-build`, `/zero-shot-fix`, `/zero-shot-sync`.

---

## How to Use This

```bash
git clone <this repo> crimanalyze && cd crimanalyze
python -m pip install -e . pytest
cp .env.example .env        # set exactly ONE provider key (Anthropic / Gemini / OpenRouter)
python agent.py             # verify setup (doctor)
python agent.py --run       # start server
```

| URL | What |
|-----|------|
| `http://localhost:8001/app/` | **UI** — upload CSVs, ask a question |
| `http://localhost:8001/health` | Health + active provider |
| `http://localhost:8001/docs` | Interactive API docs |

Tests:
```bash
python -m pytest tests/unit -q          # no key needed
python -m pytest tests/ -q              # + integration against real provider (needs key in .env)
```

---

## Repo Layout

```
src/                ← agent: api/ config/ db/ domain/ graph/ llm/ prompts/ observability/ summarizer.py
frontend/public/    ← UI: index.html + styles.css + app.js
tests/              ← unit/ (no key) + integration/ (real key)
spec/               ← roadmap, architecture, capabilities/analyze.md, data, api, ui, agent
harness/
  rules/            ← ai-agents, git, secret-hygiene
  patterns/         ← spec-driven, phases, project-layout, tech-stack, code, test-driven,
                       ui-ux, agentic-ai, engineering-practices
  skills/           ← zero-shot-build / zero-shot-fix / zero-shot-sync
  agents/           ← spec-writer, code-generator, qa-auditor
AGENTS.md           ← session entry point
agent.py            ← doctor / --run serve
```

**Capability surfaces** for this agent:
- `src/graph/nodes.py` → `analyze_data` node
- `src/prompts/analyze.md` → system prompt
- `frontend/public/` → multi-file analyst UI
- `src/summarizer.py` → CSV schema + head/tail summarization for the prompt

---

## Phase 1 — Multi-CSV Analyst

Upload 1–12 CSV files, ask a natural-language question, get an insight grounded in the data with a chart spec.

## Phase 2 — MsSQL Federation + Cache

> Assumed: read-only MsSQL connector with query fingerprinting, SQLite-backed aggregate cache, configurable TTL, cache-hit telemetry in run metadata.

Repeated identical questions answer from cache; cache latency under 1s; live query latency under 5s. Adds `AGENT_DATABASE_URL_MSSQL` to `.env`.

---

## FAQ

**What if I already have a stack in mind?**
State it at intake and the spec-writer records it as binding.

**What if something breaks?**
`/zero-shot-fix [what's broken]` — qa-auditor classifies SPEC vs CODE, the generator fixes, then re-gates.

**What if spec and code drift?**
`/zero-shot-sync` — qa-auditor audits, generators fix, spec wins.

**Why did my build branch not merge to main?**
By design. `main` is boilerplate-only — ABSOLUTELY. Builds live on feature branches whose PRs target the branch they were cut from.
