# Hermes — Entry Point

This is a spec-driven AI-agent boilerplate for **Hermes**. Read this file first, every
session, then follow the instructions below.

## What This Repo Is

A starting template for building AI agents spec-first, with a **working baseline agent
committed in `src/`** (FastAPI + LangGraph + SQLite; provider-agnostic LLM — Anthropic,
Gemini, or OpenRouter via `.env`). `uv run pytest tests/unit -q` passes on a fresh clone.
The spec in `spec/` is either:

- **Filled in** — you are implementing an agent from a completed spec
- **Empty / placeholder** — run `/zero-shot-build` to drive the spec and the build

## The Execution Model (Hermes-native — this governs everything)

**The ROOT SESSION is the orchestrator.** It alone owns:
- the **human channel** — `clarify` questions (plain-text one-by-one fallback), gates, blockers
- **git / branch / PR / commit+push**
- the **server lifecycle** — booting, smoking, and keeping the app serving for the user

The three specialist roles in `harness/agents/` are **dual-mode**: run them via
`delegate_task` when it is available (parallel for independent slices), or **inline** —
the root reads the role file as a checklist — when delegation is capped or a worker
stalls. Delegated workers cannot spawn workers (`max_spawn_depth=1`), cannot talk to the
user, may return early (the root verifies every handback: files exist, gates really ran),
and their background processes are killed on return.

| Role | Job | Mode |
|------|-----|------|
| spec-writer | The single design authority — writes the FULL spec (architecture + agent-graph + phased plan) and self-reviews it | delegate or inline |
| code-generator | Implements ONE independent slice (backend `src/`, frontend, or both) plus its tests | delegate (parallel per slice) or inline (sequential) |
| qa-auditor | Independent read-only review + runs the real gates + drift audits; classifies SPEC-vs-CODE in fix/sync | delegate or inline |

The build loop per slice: **implement → run the REAL gate → read the actual output → fix →
re-run.** Never claim, always observe.

## Your First Action Every Session

1. Read `harness/rules/ai-agents.md` — mandatory rules for all sessions
2. Check whether `spec/roadmap.md` has been filled in:
   - Contains `<!-- FILL IN -->` → the spec is not ready; do not write application code;
     point the user at `/zero-shot-build`
   - Filled in → read the full spec manifest below before touching code

## Spec Manifest (read in this order when spec is complete)

```
spec/roadmap.md
spec/architecture.md
spec/capabilities/          ← all files
spec/data.md
spec/api.md
spec/ui.md
spec/agent.md               ← REQUIRED for any agent-framework project
harness/rules/ai-agents.md
harness/patterns/spec-driven.md
harness/patterns/phases.md
harness/patterns/project-layout.md
harness/patterns/engineering-practices.md
harness/patterns/test-driven.md
harness/patterns/ui-ux.md
harness/patterns/tech-stack.md     ← generic stack rules (chosen stack is in spec/architecture.md)
harness/patterns/code.md           ← generic code conventions
harness/patterns/agentic-ai.md     ← catalogue of agentic patterns (chosen graph is in spec/agent.md)
harness/rules/git.md
```

**`spec/agent.md` is mandatory** for any project using LangGraph or another orchestration
framework. If it does not exist when you need it, stop and raise it as a blocker.

## Skills (entry points)

The skills live at `harness/skills/<name>/SKILL.md`. **The user invokes them in plain
English — no slash command needed.** Classify each request into EXACTLY ONE of the three
skills, then READ the matching `SKILL.md` and follow it exactly (the `SKILL.md` is the
process; never improvise one):
- **build** — create a new agent or add a capability → `harness/skills/zero-shot-build/SKILL.md`
- **fix** — a bug / error / failing test / defect → `harness/skills/zero-shot-fix/SKILL.md`
- **sync** — reconcile spec ↔ code (spec wins) → `harness/skills/zero-shot-sync/SKILL.md`

The outcome is always one of these three — nothing built yet ⇒ default to **build**;
genuinely ambiguous ⇒ ask one short clarifying question first. **A build-shaped message IS
the argument: start intake in that same turn — never ask the user to re-submit the idea or
invoke the skill themselves** (`disable-model-invocation` means only you can start it).
(`.hermes.md` holds the authoritative router. The `/zero-shot-*` slash commands are optional
and require registering this clone via `skills.external_dirs`.)

| Skill | Purpose |
|-------|---------|
| `/zero-shot-build [idea]` | Idea → working, verified, phased agent. Also adds a capability to an existing agent. |
| `/zero-shot-fix [target]` | Diagnose + fix a bug/error/failing test/drift, then verify. |
| `/zero-shot-sync [scope]` | Reconcile spec ↔ code (spec wins), then verify. |

## Key Rules (summary — full rules in harness/rules/ai-agents.md)

- Never write application code before reading the full spec
- Never skip a phase; the human tests each phase before the next starts
- The root session owns the run at every human gate: boot with the pinned interpreter
  (`.venv/bin/python -m src`), verify live, hand ONE URL — the user never runs a terminal
  command to test
- Commit + push are one atomic action; a PR exists before the first feature commit;
  `main` is boilerplate-only — ABSOLUTELY (builds branch from current HEAD, PR `--base $base`)
- Tests and gates run against the real LLM/API with keys from `.env` — a stubbed pass is
  not a pass; a present-but-dead key is a BLOCKER naming the env var
- One batched LLM call per artifact — never a call per output line/token
- When in doubt, ask at intake; empty answer = lowest-risk default recorded as `Assumed:`

## The Baseline in `src/` (the capability slot)

`src/` is a working agent whose capability slot is `transform_text`. Tests pass out of the
box. Generators extend it in place — never copy or rename. Replace three surfaces:

- `src/graph/nodes.py` — the `transform_text` node → your capability logic
- `src/prompts/transform.md` → your system prompt
- `frontend/public/` → your UI (zero-build static, served at `/app`)

Everything else — graph assembly, runner, API envelope, DB session, settings, the
Anthropic/Gemini/OpenRouter provider layer, structured logging, test fixtures — is wired
and tested. Full layout: `harness/patterns/project-layout.md`.
