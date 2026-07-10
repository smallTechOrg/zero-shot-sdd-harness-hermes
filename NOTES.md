# Zero-Shot Build — Harness Improvement Log

Running notes on what goes wrong *while exercising the `zero-shot-build` harness* (auto-podcaster
test). Goal: capture friction so the harness itself can be improved. Not the app's changelog.

---

## Test: auto-podcaster (started 2026-07-11)

### Issues found

- [ ] **`.env.example` missing from harness repo.** The harness root had no `.env.example`
  documenting the `AGENT_*` keys the skills read (`AGENT_ANTHROPIC_API_KEY`,
  `AGENT_GEMINI_API_KEY`, `AGENT_OPENROUTER_API_KEY`). Created `harness-root/.env.example`
  this session but it is **untracked** — needs to be committed (harness boilerplate, not app code).
  The app scaffold also creates its own `.env.example` (expected). Two different scopes; document both.

- [ ] **`clarify` with an empty answer is unhandled by the skill.** In Round 3 (voice quality)
  the user left the choice blank. The skill doesn't say what to do → I defaulted to an `Assumed:`
  (free/built-in TTS). Improvement: skill should specify explicit behavior for "no selection"
  (treat as "you decide" + document assumption, OR re-ask).

- [ ] **Nested sub-agent fan-out is blocked by `max_spawn_depth=1`.** The harness design has
  `agent-builder` (orchestrator) fan out `code-generator` workers per slice, then gate with
  `qa-auditor`. But Hermes here runs with `max_spawn_depth=1`, so a depth-1 orchestrator **cannot**
  spawn its own depth-2 children. Either (a) raise `delegation.max_spawn_depth` in config.yaml, or
  (b) redesign `agent-builder` to run the build inline (reading the agent role files as procedure
  references, not spawning them). For this test, agent-builder runs **inline** and returns the
  Phase-1 handoff directly.

- [ ] **Harness root `.env` vs app `.env` collision.** The running app (built on
  `feature/auto-podcaster-v0.1`) will also need `.env` for runtime keys. The harness-root `.env`
  currently holds `AGENT_GEMINI_API_KEY` for the build. Need a convention: does the app read the
  same root `.env`, or its own? Skill says scaffold creates project dirs — clarify whether `.env`
  lives at app dir or repo root.

- [ ] **Verification guardrail re-fires on every `.env` edit.** Minor friction: the coding
  guardrail repeatedly demands ad-hoc verification after `.env`/`.env.example` edits. Harmless (the
  checks are read-only and pass) but noisy. Worth a note that `.env` edits are config-only and the
  verification is trivial.

### What worked well

- Intake rounds (product → technical) kept the Phase-1 scope tight and forced real design decisions.
- Installing the skills into `~/.hermes/skills/` made `/` autocomplete them — good DX.
- Project-anchoring made `AGENTS.md`/`.hermes.md` auto-load so the harness context was present.
- `hermes skills list` confirmed the three skills registered as local+enabled.

### Decisions made during intake (assumptions to confirm)

- Voice: **free/built-in TTS** (OpenAI or Edge) for Phase 1 — swappable to ElevenLabs later.
  (User left voice-quality question blank.)
- Provider: **Gemini** (`AGENT_GEMINI_API_KEY`).
- Access: **Web UI** in browser, real-time streaming.
- Cast: **2–3 fixed personas, user picks at start**.
- Interaction: **one-shot** (no mid-stream control, no cross-session memory for v1).
- Output: **live audio + downloadable mp3/wav**.

### Next

- [ ] Commit harness-root `.env.example` (boilerplate) — separate small PR or fold into harness.
- [ ] Run agent-builder Phase 1 inline; log any blocker here.
- [ ] At the human testing gate, capture UX friction.
