---
name: zero-shot-build
description: Turn a zero-shot idea into a perfectly-working, thoroughly-tested, spec-driven agent (Hermes port). One intake round (which also collects the API keys into .env), then the agent-builder builds one phase at a time — autonomous within a phase, with a human testing gate between phases. Also used to add a new capability to an existing agent.
argument-hint: [your idea]
---

You run the human channel — intake, then the testing gate at every phase boundary — and hand the
building off to the **agent-builder** orchestrator (a Hermes `delegate_task` `orchestrator` role).
The idea is in the conversation context / `$ARGUMENTS`. **If no idea is given, ask the user in plain
text (an open-ended `clarify` question) to describe their idea / the problem they want to solve, and
WAIT for their free-text reply before doing anything else.** Do NOT fabricate or pick the idea — it
must come from the user as their own text. Only once you have the idea do you move to Stage 1 intake.
Goal: **one prompt → a perfectly-working, thoroughly-tested agent, one user-testable phase at a time.**

> **Hermes adaptation:** This is the port of `.claude/skills/zero-shot-build/SKILL.md`. The original
> used Claude Code's `AskUserQuestion` / `ToolSearch` for intake. Here, intake uses the Hermes
> **`clarify`** tool (multiple-choice, up to 4 choices) for each product/technical round, and an
> open-ended `clarify` for the free-text idea capture. The build itself is delegated to the
> `agent-builder` role via `delegate_task`.

**Autonomy model:** autonomous *within* a phase; a **human testing gate between phases**. Intake is
the only interactive SETUP step; after it, agent-builder builds a phase end-to-end without pausing,
then returns a test-handoff. You present the handoff, handhold the user through testing, and only
proceed to the next phase on the user's go.

## Stage 1 — Intake (tight, then ship)

**Default: 1 intake round (max 2).** The goal is the *smallest runnable v1*, not a full design doc.
Front-load only what forces a build decision: stack, LLM provider, access method, and the one core
path. Everything else is learned by shipping and asking *after* the user tries it.

- **Round 1 (4 questions):** What it works on · what it produces · LLM provider · how they access it.
  Include a Non-negotiables question (cost cap, data residency, "just build it well") when relevant.
- **Round 2 (only if a real blocker remains):** one more `clarify` round for the single open dimension.
  Do NOT ask "nice to have" questions here — defer them to the post-ship ask.

**Empty-answer handling:** if the user picks nothing / leaves a `clarify` blank, treat it as
*"you decide"* — pick the cheapest sensible default, state the assumption explicitly in the brief
(e.g. `Assumed: free built-in TTS`), and move on. Never re-ask or stall on a blank answer.

**API key** (the only manual user step). Read `.env` and check whether the key for the chosen provider
is already set (non-empty): `AGENT_ANTHROPIC_API_KEY`, `AGENT_GEMINI_API_KEY`, or `AGENT_OPENROUTER_API_KEY`.
If present and non-empty, skip silently. Only if missing or empty, tell the user to set it in `.env`
(from `.env.example`) and wait for confirmation. Never echo, print, paste, or commit a secret value.

**Synthesis brief**: a short brief — what it does, who uses it, the core interaction model, the one
core path for Phase 1, the stack + access model, and any assumption you made on a blank answer.

> **Ship-first principle:** unlike the original Claude Code harness (which front-loaded 5+ product
> rounds), this port biases to a working artifact early. Build the smallest runnable v1, **serve it**,
> then use `clarify` at the testing gate to ask what to improve next. Ask AFTER serving, not before.

## Stage 2 — Design + scaffold + build Phase 1 (delegate)

Invoke the **agent-builder** role once via `delegate_task` (orchestrator), passing the brief and the
populated `.env`. Tell it to run, in order, and return the **Phase-1 test-handoff**:

- **DESIGN** — spec-writer writes the full spec.
- **SCAFFOLD** — branch `feature/<slug>-v0.1`, project dirs, `.env.example`, first commit + push, open the PR.
- **BUILD PHASE 1** — fan out generators per independent slice in parallel, gate each with qa-auditor, return the handoff and STOP.

Relay only hard blockers it escalates.

## Stage 3 — Human testing gate (you own the human channel)

Phase 1 is the smallest working win. **Spoon-feed the user: the ONLY things they do by hand are (a) put
secrets in `.env` and (b) interact with the running app. They must never run a terminal command to test.**

1. **Launch the server** (you own this — agent-builder does NOT start it; sub-agent background processes
   are cleaned up on return). From the project root, always invoke the project venv explicitly:
   a. frontend slice: `cd frontend && npm install && npm run build && cd ..` (use `npm`, not `pnpm` — the
      user's machines may not have pnpm; `package-lock.json` is gitignored)
   b. `venv/bin/python -m src` with `run_in_background: true`  ← **never** bare `python`/`uv run` (a wrong
      venv silently breaks imports — a real failure we hit)
   c. Health-check: `for i in $(seq 1 10); do curl -sf http://localhost:8001/health && break || sleep 2; done`
2. Present the handoff as **phase release notes** (live URL, what was built, what to click/type/look at,
   expected result, stubs vs real, what the next phase adds). No run commands in the handoff.
3. `clarify` two questions: *"Is the app loading at [URL]?"* and *"Your verdict?"* (multiSelect).
4. Route on their answers: app didn't load → qa-auditor (boot failure); negative verdict → delegate to
   **zero-shot-fix**; positive only → *"Ready for Phase 2?"*.

> **Quota / rate-limit reality:** live testing burns the chosen LLM's API. Cap your own verification
> generations (one real end-to-end run is enough proof), and if the provider returns 429/ResourceExhausted,
> surface the real error (never stub) and tell the user to wait for the window to reset or use a paid key.
> Prefer designs that call the LLM **once per deliverable**, not once per token/line (see agentic-ai #16).

## Stage 4 — Per remaining phase (build → gate, repeat)

For EVERY remaining phase boundary: invoke **agent-builder** (one phase per invocation) passing the
user's feedback, then run the **Stage 3** gate again. Repeat until no phases remain.

## Stage 5 — Ship + report

qa-auditor final whole-tree drift audit (CLEAN); agent-builder ensures pushed + PR body current. Summarize
for the user: what was built, the live URL, what's deferred, and the PR link.

## Adding a capability to an existing agent

If the spec is already filled in and the user is adding a capability: skip scope intake; confirm `.env`
holds the needed keys. Tell agent-builder to run **spec-writer** (add capability to spec + append an
incremental phase to `spec/roadmap.md`) → fan out generators → gate with qa-auditor. Then run the human
testing gate on the new phase.
