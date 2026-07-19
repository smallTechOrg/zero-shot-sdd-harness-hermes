# Implementation Phases

Agents are built phase by phase, derived from the user's requirements — not a fixed ladder. **Phase 1 is the smallest user-testable win that works first time;** each later phase wires a stub into a real feature. Production concerns trail behind the requirements.

## Core Principle

**Smallest win first, then complete, then polish.**

Phase 1 is the SMALLEST user-testable win that works the FIRST time the user tests it — real on the one core path, with clearly-labelled stubs for everything else (this is the same rule the spec-writer applies; the two must agree). It is fine for Phase 1 to be smaller than "complete" — what matters is that the one path it delivers is real and impresses, not that it covers every requirement. Later phases wire the labelled stubs into real features, one human-tested increment at a time. Do NOT over-scope Phase 1 to cover "all the primary requirements" — that is the over-build that doubles build time and breaks first-time-right.

The spec-writer derives the phase breakdown from `spec/roadmap.md` — the count and names come from the requirements, not a fixed ladder.

## Phase Structure

Four roles are always present; the middle phases are derived from requirements:

---

### Phase 1 — First Win

Phase 1 is the **smallest user-testable win** — the full primary user journey end-to-end, real and working the first time, that the person who briefed the idea immediately appreciates. Not every feature: the complete primary flow, done right, with supporting features as labelled stubs.

- **Full primary journey, not "all the features."** Deliver the complete end-to-end flow that proves the idea (e.g. upload → profile → ask → answer-with-chart) — every step the user must take to get a real result. Defer secondary features (export, history, multi-file, settings) to later phases as clearly-labelled stubs. Over-scoping Phase 1 to cover every feature is the failure mode, not the goal.
- **Agentic stack is wired from day one.** The graph framework (LangGraph or equivalent), state type, core nodes, and assembly are set up in Phase 1 even if some capability nodes are stubs. Never defer the agentic skeleton.
- Frontend is visually complete: real UI for the one path Phase 1 delivers, PLUS clearly-labelled stubs for what's coming. Stubs are never mistaken for bugs.
- All calls on the tested path hit the real LLM/API (keys from `.env`) — no fake data on what the user tests.
- **Gate (all must pass):**
  1. `pyproject.toml` declares the DB driver in `[project.dependencies]` (e.g. `psycopg2-binary` for PostgreSQL) — never dev-only
  2. If the schema changed from the baseline: `uv run alembic upgrade head` succeeds and `uv run alembic current` prints a revision — run and confirmed against the same DB the server uses (a stale dev DB turns a green suite into a live 500)
  3. **Boots via the documented run command** — the app starts on its exact README/roadmap run command from the repo root with the pinned interpreter (`.venv/bin/python -m src` / `uv run python -m src`) with no `ImportError`/`ModuleNotFoundError`. A green pytest run does NOT prove this (pytest's path masks `src.`-prefixed import bugs); the test path must equal the run path. **Launch it with the terminal tool's background flag (`background=true`/`run_in_background`), never a `&`-backgrounded command, `nohup`, `setsid`, or `disown`** — Hermes hard-blocks those; health-check in a follow-up terminal call (each call starts fresh at repo root, so use absolute paths or `cd X && cmd`).
  4. Primary user journey works end-to-end against the real LLM/API; tests pass
  5. **Agentic stack gate:** graph compiles, state flows through nodes, agent is invocable — confirmed by the Phase 1 test
  6. **Rendered-UI check (any UI surface):** the served page at the single-origin path (`:8001/app/`) contains the phase's real UI, and its linked CSS/JS assets return 200 non-empty. If the project adopted a JS framework: the production build ran and its built output is what's served, styled. An unstyled or empty 200 fails the gate.
  7. **Live-server E2E (any UI/HTTP surface):** a smoke against the live app walks the primary user journey and asserts real output content appears — not just a 200. (Headless-browser tooling e.g. Playwright is required only for client-side-rendered frameworks; the zero-build static frontend is gated with TestClient/httpx content assertions.)
  8. **Observability wired:** structured request/response logging to stdout confirmed working — a log line appears for the Phase 1 end-to-end run. Observability is never deferred.
  9. Working tree is clean and committed
  10. Phase test-handoff published; the human has tested and approved (see Human Testing Gate)

---

### Phases 2–N — Requirements Phases *(spec-writer derives these)*

Each phase covers a chunk of remaining user requirements from `spec/roadmap.md`. The spec-writer **names these phases after what they deliver**, not after generic production concerns. Aim for all user requirements covered by phase 2–3 — fewer, bigger phases beat many thin ones.

- Each phase wires Phase-1 stubs into real functionality — a **minimum of 3 capabilities per phase**. Never deliver a single capability in isolation; group related capabilities that form a coherent user story and build them together. A phase with fewer than 3 capabilities is too thin — collapse it into the adjacent phase.
- All external calls hit the real provider using keys from `.env`; tests assert on real responses (shape/content), not hardcoded strings.
- **Gate:** The phase's user-testable increment works end-to-end against the real LLM/API; tests pass; working tree clean; human approved.

---

### Phase N+1 — Agentic Stack Upgrade + Resilience *(only if `spec/agent.md` calls for patterns beyond the base loop)*

If the spec's agent graph needs more than the base ReAct loop, add a phase to upgrade the agentic architecture and harden external calls. A simple single-loop agent that already meets its requirements does not need this phase — do not add it by default.

- **Upgrade the agentic stack** per `spec/agent.md`: wire in the patterns it calls for beyond the base ReAct loop — planning, reflection, multi-agent coordination, memory, or whatever the spec requires. Phase 1 laid the skeleton; this phase promotes it to the production-grade architecture.
- Add error handling to all external calls: try/except, retries, timeouts. Agent continues (degraded, not crashed) on non-critical failures.
- **Gate (all must pass):**
  1. Every pattern listed in `spec/agent.md` beyond the base loop is wired and exercised by a real test
  2. Agent handles all documented failure modes without crashing

---

### Phase N+2 — Complete Agentic System *(the final requirements phase — every capability real)*

The last phase turns the remaining labelled stubs into real features so every capability in `spec/roadmap.md` is active and the system runs fully end-to-end. (When the agent is simple, this is just the last requirements phase — not a separate agentic milestone.)

- Every capability in `spec/roadmap.md` is real — no stubs on any active path.
- Complete any remaining integrations; system runs against all real services.
- **Gate (all must pass):**
  1. All integrations are real; agent runs fully end-to-end against the real LLM/API
  2. Every capability in the spec is implemented and tested with real data
  3. `spec/agent.md` graph matches the running code — drift audit passes on the agentic surfaces

---

### Trailing Phases *(only if the spec requires them)*

These phases exist only when the spec explicitly calls for them — never as defaults:

- **API / CLI Surface** — only if `spec/api.md` calls for an external API or CLI
- **UI Polish** — only if `spec/ui.md` calls for further UI work beyond Phase 1
- **Advanced Observability** — dashboards, metrics, alerting beyond the basic LangSmith tracing + structured logging already wired in Phase 1
- **Polish + Hand-off** — final drift audit; README verified end-to-end from a clean clone; user accepts hand-off

---

## Human Testing Gate

The build is autonomous WITHIN a phase, with a human testing gate BETWEEN phases — at EVERY phase boundary.

After a phase passes its automated gate and is committed, the build publishes a **test-handoff** and STOPS:
- The handoff gives exact run commands, what to click/look at, the expected result, and what is a labelled stub vs. real.
- Only the root session presents it and asks the human.
- The next phase starts ONLY after the human approves.
- On a reported issue → qa-auditor diagnoses and routes → the right generator (frontend and/or backend) fixes → re-gate → re-present.

## Parallel Slices Within a Phase

- spec-writer carves each phase into INDEPENDENT SLICES (the parallel units) with explicit dependencies; default to independence so slices build concurrently.
- The root session runs the code-generator role per slice — delegated in parallel when `delegate_task` is available (disjoint paths: frontend slices write the frontend surface, backend slices write `src/` — never the same file), sequentially inline otherwise. qa-auditor gates each slice as it lands.
- Serialize ONLY across a true declared dependency. On a BLOCKED slice, loop only that slice's generator; other slices are unaffected. For headless/CLI builds, only backend slices exist.

## Phase Gates

A phase is complete when ALL of the following are true:
1. All code for the phase is committed and pushed
2. All tests for the phase pass
3. Working tree is clean
4. Phase test-handoff published; (build) human tested and approved
5. The qa-auditor role (delegated or run inline by the root session) has signed off
6. If the phase changed the schema: `alembic upgrade head` has been run against the real DB and succeeded
7. **README updated** — every command, env var, setup step, route, or capability this phase added is reflected in `README.md`, and every README command in scope has been run and confirmed to work from the stated directory. A stale README is a BLOCKER.

**Never mark a phase complete if any gate is red.**

**Never claim a phase passes based on tests alone if those tests use a different DB driver than production.** SQLite tests passing does not mean PostgreSQL migrations work.

**Never claim Phase 2+ passes on stubbed providers** — the gate runs against the real LLM/API with keys from `.env`.

## Phase Tracking

The current phase is recorded in git commit messages (`phase-N: [description]`). To see phase history, run `git log --oneline | grep "phase-"`.

## Adapting the Phases

The spec-writer derives the phases from `spec/roadmap.md`. What is fixed:

- **Phase 1 is always the smallest user-testable win** — the one core path real and first-time-right, the rest as labelled stubs (this matches `spec-writer.md` exactly; the two never disagree)
- **The agentic stack is always wired in Phase 1** — graph, state, nodes, assembly; never deferred (the skeleton is wired even though most nodes start as stubs)
- **An Agentic Stack Upgrade phase and a Complete Agentic System phase are added only when `spec/agent.md` calls for patterns beyond the base loop** — a simple agent that meets its requirements does not get them by default
- **Trailing phases are only added when the spec explicitly requires them**

What varies (derived from requirements):
- How many requirements phases (2–N) — count comes from `spec/roadmap.md`; target 1–2 requirements phases. Each must contain at least 3 capabilities — if a phase would have fewer, collapse it into the adjacent one.
- Names of requirements phases — named after what they deliver (e.g. "Profiling + Charts + Export", "History + Multi-file + Settings"), not generic concerns

---

## Language-Specific Gate Commands

The spec-writer sets the exact gate command per phase in `spec/roadmap.md` (## Phases of Development), honoring the test rules in `harness/patterns/tech-stack.md`.

| Language | Phase 1 gate | Phase 2+ gate |
|----------|-------------|-------------|
| Python | `uv run alembic upgrade head` + `uv run pytest` | `uv run pytest` (PostgreSQL, automated via conftest) |
| TypeScript (Bun) | migration tool + `bun test tests/unit/` | `bun test tests/integration/` |
| TypeScript (Node) | migration tool + `npx vitest run tests/unit/` | `npx vitest run tests/integration/` |
| Go | `migrate up` + `go test ./internal/...` | `go test ./...` |

Phase 2+ gates run with **real LLM/API keys loaded from `.env`** regardless of language; both the DB URL and the provider key(s) must be set.

## TypeScript/Bun Integration Test Pattern

```typescript
// tests/integration/pipeline.test.ts
import { describe, it, expect, beforeEach } from "bun:test";

// Use the production DB driver via conftest-style setup/teardown — never SQLite-as-a-substitute
// Call the real LLM/API using keys from .env

describe("pipeline", () => {
  it("runs end-to-end against the real provider", async () => {
    // call runner against the real provider
    // assert DB record created with correct status
  });
});
```
