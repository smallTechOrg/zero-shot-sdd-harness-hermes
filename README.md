# Zero-Shot SDD Harness for Building Agents — Hermes Native

Give it a one-line idea. Walk away with a working, tested, phased agent.

A lean, **Hermes-native** harness for building agentic software **spec-first**. One person
with an idea and one API key can drive a real, production-shaped agent into existence — and
a senior engineer opening the result finds a conventional, reviewable stack, not generated
mush.

---

## The Spirit

Six convictions the whole repo is built around:

1. **Spec is the source of truth.** Written before the code, always. When spec and code disagree, the spec wins and the code is fixed (`/zero-shot-sync`).
2. **Built for two audiences at once.** A non-coder drives it with a single sentence; a senior engineer inherits a clean FastAPI + LangGraph stack they can read, review, and own.
3. **Lean harness, not a framework.** `harness/` is engineering *mindfulness* — rules and patterns that keep every session consistent. The product runtime is **NVIDIA NIM by default** with OpenAI-compatible fallbacks.
4. **Smallest first-time-right win, phase by phase.** Each phase ships the smallest increment a human can actually test, and it must work the *first* time they test it.
5. **A human gates every phase.** Autonomous *within* a phase; stops at each boundary for you to test the increment.
6. **Real LLM/API or it doesn't count.** Gates and tests run against the real model with keys from `.env`. A stubbed pass is not a pass.

---

## What This Is

A working **baseline agent** in `src/` — FastAPI + LangGraph + SQLite for CSV mode, read-only MsSQL via SQLAlchemy for live queries, fraud-detection analyst panel, run history + audit export, and a static frontend served by the backend at `/app`.
- A **zero-build static frontend** in `frontend/public/` served by the backend at `/app` —
  no npm, no bundler, nothing to break at clone time.
- A **spec template** in `spec/` — roadmap, architecture, capabilities, data, api, ui, and
  the agent graph.
- Three **skills**: `/zero-shot-build`, `/zero-shot-fix`, `/zero-shot-sync`.
- Three **dual-mode specialist roles** (`harness/agents/`): spec-writer, code-generator,
  qa-auditor — delegated when the runtime allows, executed inline by the root session
  otherwise.
- **A human testing gate between phases** — you click a live URL; you never run a terminal
  command to test.

## The Hermes-Native Architecture

The original Claude-Code harness delegated the whole build to an orchestrator sub-agent
that fanned out workers. Hermes caps delegation depth (`max_spawn_depth=1`), so that design
silently degrades. This port makes the constraint the architecture:

```
YOU (idea, .env key, clicking the app)
 │
ROOT SESSION — the orchestrator. Owns: human channel (clarify), git/PR, server lifecycle.
 │
 ├─ spec-writer      ─ full spec + phased plan, self-reviewed        (delegate or inline)
 ├─ code-generator   ─ one slice + tests, per slice                  (parallel or inline)
 └─ qa-auditor       ─ read-only review + runs the REAL gates        (delegate or inline)
 │
per phase:  implement → run real gate → READ output → fix → re-run
            → boot on the documented command → live smoke → commit+push
            → HUMAN GATE: one live URL + multi-select checklist
```

Three properties make it robust on Hermes:

- **Inline fallback everywhere.** Delegation is an optimization, never a dependency — the
  root executes any role file as a checklist when workers can't spawn.
- **Trust-but-verify handbacks.** Workers routinely return at "95% done"; the root checks
  the files, re-runs the gate, and finishes remainders itself.
- **The gate owns the run.** Only the root launches servers (workers' processes die on
  return), with the pinned interpreter on a verified free port — you get ONE live URL that
  has already been smoke-tested.

---

## How to Use This

```bash
git clone <this repo> my-agent && cd my-agent
cp .env.example .env # set an NVIDIA NIM key via OPENAI_API_KEY + OPENAI_BASE_URL, or use another OpenAI-compatible key
```

Then open a Hermes session anchored to the repo and **just say what you want, in plain
English** — no slash command, no setup:

```
Build me an agent that monitors my Shopify store for low-inventory products and drafts restock emails.
```

Hermes auto-loads `.hermes.md` from the repo, which **routes your request to exactly one of
three skills** and follows it:

- **build** — "build me an agent that…", "add X to it" → creates the agent / adds a capability
- **fix** — "it's erroring on…", "the tests fail", "X doesn't work" → diagnoses + fixes, then verifies
- **sync** — "make the code match the spec", "reconcile the drift" → reconciles spec ↔ code (spec wins)

You never pick the skill — describe the goal and the harness chooses. One deep intake (which
also collects your API key into `.env`), then the build runs one phase at a time and stops at
each boundary with a live URL for you to test.

**Prefer the `/zero-shot-build` slash command?** Hermes only recognises slash commands that
are registered — an unregistered one returns "Unknown command". Register this clone once
(one line, tracks the repo, nothing to re-run after `git pull`), then restart Hermes:

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - /absolute/path/to/this/clone/harness/skills
```

*Optional / preflight:* `uv run pytest tests/unit -q` runs the local sanity checks (no live LLM required). Not required to start the server.

## What Happens

```
Your idea
    ↓
INTAKE — multi-round product questions (idea-specific, multi-select), then one technical
         round; fill .env; the key is VALIDATED with a real call before building
    ↓
[spec-writer]  → full spec: capabilities + architecture + agent graph + phased plan
    ↓
[root session] → feature branch + PR (base = the branch you were on, never main)
    ↓
per phase:  code-generator per slice → qa-auditor gates each → boot + live smoke
            → commit + push → HUMAN GATE (live URL + what-worked checklist)
    ↓
repeat per phase → final drift audit → SHIP
```

---

## Running the App Now

```bash
# all commands run from the repo root
uv sync
cp .env.example .env
uv run pytest -q
uv run python -m src
```

|| URL | What |
|-----|------|
| `http://localhost:8001/app/` | **UI** — CSV upload/Q&A, Live DB, Fraud detection, History |
| `http://localhost:8001/health` | Health + active provider (never key values) |
| `http://localhost:8001/docs` | Interactive API docs (Swagger) |

Tests:

```bash
uv run pytest tests/unit -q # no key needed
uv run pytest tests -q # full gate, integration routes need a configured key in .env
```

## Repo Layout

```
src/                ← baseline agent: api/ config/ db/ domain/ graph/ llm/ prompts/ observability/
frontend/public/    ← zero-build static UI (index.html + styles.css + app.js), served at /app
tests/              ← unit/ (no key) + integration/ (real key)
spec/               ← your spec: roadmap, architecture, capabilities/, data, api, ui, agent
harness/
  rules/            ← ai-agents, git, secret-hygiene
  patterns/         ← spec-driven, phases, project-layout, tech-stack, code, test-driven,
                      ui-ux, agentic-ai, engineering-practices
  skills/           ← zero-shot-build / zero-shot-fix / zero-shot-sync (SKILL.md each)
  agents/           ← spec-writer, code-generator, qa-auditor (dual-mode role files)
AGENTS.md           ← the session entry point
agent.py            ← doctor (default) / --run (serve)
alembic/            ← migrations, wired (empty until the first schema change)
.env.example
```

**Capability slots / entry surfaces**:
- `src/api/csv.py` — CSV analyst endpoint
- `src/api/live_db.py` — live read-only database queries
- `src/api/fraud_detection.py` — fraud-signal analyst over schema metadata
- `src/api/runs.py` — run history + audit export
- `src/prompts/` — prompt files per analyst path
- `frontend/public/` — static UI served at `/app`

Everything else (graph wiring, API, DB, settings, providers, tests) is already working.

---

## FAQ

**What if I already have a stack in mind?**
State it in the idea: `/zero-shot-build [idea] — use Python + FastAPI + PostgreSQL`. Stack
choices are binding.

**What if something breaks?**
`/zero-shot-fix [what's broken]` — qa-auditor classifies SPEC vs CODE, the generator role
fixes, qa-auditor re-gates, the root commits + pushes.

**What if spec and code drift?**
`/zero-shot-sync` — qa-auditor audits, generators fix, spec wins.

**Why did my build branch not merge to main?**
By design. `main` is boilerplate-only — ABSOLUTELY. Builds live on feature branches whose
PRs target the branch they were cut from.
