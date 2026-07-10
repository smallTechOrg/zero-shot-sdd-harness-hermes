# Zero-Shot Build — Harness Improvement Log

Running notes on what goes wrong *while exercising the `zero-shot-build` harness* (auto-podcaster
test). Goal: capture friction so the harness itself can be improved. Not the app's changelog.

---

## Test: auto-podcaster (started 2026-07-11)

### Issues found

- [x] **`.env.example` missing from harness repo.** The harness root had no `.env.example`
  documenting the `AGENT_*` keys the skills read (`AGENT_ANTHROPIC_API_KEY`,
  `AGENT_GEMINI_API_KEY`, `AGENT_OPENROUTER_API_KEY`). Created `harness-root/.env.example`
  this session — now committed on `feature/auto-podcaster-v0.1` (alongside the app's own `.env.example`).
  Two different scopes; both present now.

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

- [x] Commit harness-root `.env.example` (done on feature/auto-podcaster-v0.1).
- [x] Run agent-builder Phase 1 inline; log blockers below.
- [ ] At the human testing gate, capture UX friction (in progress — see gate below).

### Build-phase outcome (2026-07-11)

**Shipped:** PR #3 `auto-podcaster v0.1 (Phase 1)` — live two-host podcast (Gemini dialogue + edge-tts
SSE + mp3 download). Branch `feature/auto-podcaster-v0.1`, committed, pushed, PR open.

**Real verification (not stubbed):**
- `pytest tests/` -> 4 passed (real Gemini + real edge-tts, ~35s).
- Manual e2e: generated "future of remote work" hosts maya+leo -> 839KB SSE audio streamed ->
  real 615KB mp3 saved (MPEG ADTS layer III) -> `done` event. Backend + tests verified.

**Friction discovered DURING the build (harness/code, not intake):**
- [ ] **Background `delegate_task` returns before final commit/push/PR.** The sub-agent hit a
  fixable import bug and ended its turn at ~95% (no commit/push/PR). Parent had to finish:
  rename `src/graph/__init__.py` -> `dialogue.py`, fix import paths (`..config`/`..prompts`),
  fix `TestClient.stream` usage, fix host name->id mapping, add `src/__main__.py` entrypoint,
  then commit/push/PR. Harness should make agent-builder's "return handoff" explicitly include
  "commit + push + open PR before returning" as a hard gate, not optional.
- [ ] **Two Python environments caused a red-herring failure.** `.venv` (deps OK) vs the Hermes
  agent venv (`pydantic_core` broken, no `google.generativeai`). `uvicorn` launched via background
  terminal picked the wrong venv and failed; `pytest` had silently used `.venv`. Fix: always invoke
  with `.venv/bin/python -m ...` explicitly. Worth a harness rule: pin the venv path in run steps.
- [ ] **`google.generativeai` is deprecated** (warns, still works). Should migrate to `google.genai`.
  Phase-1 blocker-free but tech-debt; log as a later-phase cleanup.
- [ ] **Frontend not yet browser-tested by the human** (the actual gate). Backend+tests green;
  the Next.js play path is the gated step the user runs.

- [ ] **Live audio streaming has a browser-constraint tradeoff (learned 2026-07-11).**
  edge-tts emits ADTS MP3 frames. `MediaSource.isTypeSupported("audio/mpeg")` is `false` in
  Chrome (MSE accepts aac/mp4/webm, not raw mp3). So the "seamless live append" MSE path falls
  back to playing the COMPLETE blob once at `done` — smooth, no reset, but NOT byte-live.
  Two resets of the player happened during the test (per-chunk `play()`), fixed by (a) dropping
  per-chunk play, (b) MSE append where supported, (c) whole-blob play otherwise.
  **Phase-2 upgrade:** transcode MP3 chunks to a container MSE accepts (webm/opus via ffmpeg.wasm,
  or pipe via a real streaming muxer) to get true live progressive playback in Chrome. Track this.

- [ ] **Gemini free-tier quota (`ResourceExhausted`) bites during heavy testing (learned 2026-07-11).**
  After many generate runs in one session, `models/gemini-2.5-flash` started returning 429
  `ResourceExhausted`. The harness correctly refused to stub (DialogueError surfaced, stream emitted
  `error` event) — good. But it blocks live testing. **Harness lesson:** during a build, the agent
  should (a) cap test generations, (b) add retry/backoff on 429, and (c) tell the user to wait for
  quota reset or use a paid key. Also: the e2e test burned the quota; consider a `--limit 1` mode.

### Human testing gate (current)

You test only by interacting with the running app (no terminal commands from you). I own launching
servers. Once you try the UI, report: app loads at :3000? audio streams live? download works? I route
on your verdict (positive -> Phase 2; negative -> delegate zero-shot-fix; won't load -> qa-auditor boot check).

### User feedback on the harness (2026-07-11, during auto-podcaster test)

Live signal while running `/zero-shot-build`:

- [ ] **Intake still asks too many questions up front.** The multi-round `clarify` intake (5 product
  rounds + technical) feels heavy. The user wants the harness to **ship a working server first, then
  ask questions interactively** (via `clarify`) to refine. I.e. invert the order: build the smallest
  runnable v1 -> serve it -> ask targeted questions about what to improve. This is a direct critique
  of the skill's Stage-1 intake, which front-loads design decisions.
- [ ] **"Give me a working server, then ask questions with the user tool."** Desired loop: agent
  delivers something runnable, the user tries it, the agent asks (clarify) what to change next. This
  is the opposite of exhaustive pre-design.
- [ ] **"This Hermes port is nothing like the Claude Code harness, that used to ask me too many
  questions."** The user found the original Claude Code harness question-heavy and likes that this
  port feels different. Keep that direction: bias toward a working artifact early, fewer upfront asks.

**Harness-improvement implication:** consider tuning `zero-shot-build` so intake is capped at 1–2
rounds (just enough to pick a stack + one core path), then the build ships a runnable v1, and later
phases are driven by the user's live reactions via `clarify` at each testing gate. Extend the
"ask AFTER serving" principle into the build itself, not just the gate. Also: the agent should OWN
launching a working server (not ask the user to run terminal commands) before any post-serve questions.
