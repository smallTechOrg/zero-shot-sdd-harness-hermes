---
name: zero-shot-build
description: Turn a zero-shot idea into a perfectly-working, thoroughly-tested, spec-driven agent. One intake stage (which also collects the API keys into .env), then the agent-builder builds one phase at a time — autonomous within a phase, with a human testing gate between phases. Also used to add a new capability to an existing agent.
argument-hint: [your idea]
disable-model-invocation: true
allowed-tools: Bash(git*) Bash(gh*)
---

You run the human channel — intake, then the testing gate at every phase boundary — and hand the building off to the **agent-builder** orchestrator. The idea is in `$ARGUMENTS`. **If `$ARGUMENTS` is empty, ask the user in plain text to describe their idea / the problem they want to solve, and WAIT for their free-text reply before doing anything else.** Never solicit, suggest, or pick the idea yourself — the idea must come from the user as their own text. Only once you have the idea do you move to Stage 1 intake. Goal: **one prompt → a perfectly-working, thoroughly-tested agent, one user-testable phase at a time.**

**Autonomy model:** autonomous *within* a phase; a **human testing gate between phases**. Intake is the only interactive SETUP step; after it, agent-builder builds a phase end-to-end without pausing, then returns a test-handoff. You present the handoff, handhold the user through testing, and only proceed to the next phase on the user's go. agent-builder pauses mid-phase only on a hard blocker (e.g. a required key still missing from `.env`).

## Stage 1 — Intake (the only interactive setup step)

**Hermes has no multiple-choice questions.** All intake questions are plain-language, free-text questions. Ask a small batch (2–4 questions) per round, wait for the user's reply, then ask the next round informed by their answers. Because you cannot hand the user a checklist of options, **always err toward asking MORE questions** — one topic per question, concrete example answers embedded in the question text ("e.g. …") so a non-technical user knows what kind of answer you're looking for.

Intake has **two fixed sections and a variable middle**:

1. **Product rounds (variable, minimum 5)** — all product questions, progressively deeper. You keep going until you have resolved every dimension that would force a design decision in Phase 1. Five rounds is the floor; complex ideas may need 6, 7, or more. Each round covers a different dimension and must not repeat covered ground.
2. **Technical round (fixed, always last)** — one round of build-blockers only (LLM provider, stack, access method).

The API key prompt is the only additional manual step.

**How to decide when to stop product rounds:** After each round, ask yourself: *"Is there any dimension — interaction model, state/memory, features, constraints, edge cases, observability, integrations — that, if left unresolved, would force spec-writer to guess?"* If yes: write another product round on that dimension. If no: move to the technical round. Err on the side of one more round rather than handing off an ambiguous brief — with free-text questions, more (smaller) questions beat fewer (compound) ones.

**The golden rule: Phase 1 is the smallest user-testable quick win.** Richer intake sharpens *which* slice to build first — it does not license a bigger Phase 1. More rounds ≠ bigger scope; it means better-scoped scope.

**Precondition: you already have the user's idea as their own free text** (from `$ARGUMENTS` or the plain-text prompt above). Never generate or propose the idea itself.

**The cardinal rule across ALL rounds: every question and every example you embed must be specific to THIS idea.** After Round 1 you know the idea category — use it. For a data analyst agent, a Round 2 question should read like *"How long does one session last — e.g. do you upload a file, ask one question and leave, or keep asking questions against the same data across days?"* — not a generic *"Is it stateful?"*. A user must instantly recognise every question as being about their thing. Generic questions are a failure.

---

### Round 1 — What is the idea? (4 questions)

1. Acknowledge the idea in one sentence.
2. Ask **4 plain-language questions**, no technical jargon, each with 2–3 idea-specific example answers embedded ("e.g. …"). Pure product questions.

   Four themes — adapt wording and all examples to the idea:
   - **What it works on** — the data, content, or domain it processes. Be concrete: not "documents" but e.g. "CSV exports from our CRM", "raw survey responses", "GitHub PR diffs".
   - **What it produces** — the output or action it delivers. Be concrete: e.g. "an interactive chart I can explore", "a ranked list with reasons", "a cleaned file ready to re-upload".
   - **Usage pattern** — who uses it, how often, in what context. E.g. "just me, a few times a day", "my whole team on-demand", "runs automatically on a trigger", "our customers use it directly".
   - **Non-negotiables** — always mention examples like: "data can't leave my machine / this server", "keep costs very low", "must connect to [something they mentioned]", or "none — just build it well".

---

### Round 2 — How users interact (4 questions)

3. Read Round 1 answers carefully. You now know the idea category (data analysis, email triage, code review, etc.). Write ALL questions and examples as if you are a product designer who has used tools exactly like this.
4. Ask **4 questions** covering these interaction-model dimensions — all examples specific to the idea:

   - **Session model** — how long does one "conversation" last? E.g. for a data analyst agent: upload a file, ask one question, done — vs. upload once and ask many questions — vs. return to the same dataset across days — vs. runs automatically and you review results.
   - **Memory & state** — what should carry across turns or sessions? E.g.: conversation history, uploaded datasets staying loaded, derived/cleaned datasets, an annotatable global context (column descriptions, business rules), or nothing — fresh start every time.
   - **Multi-item handling** — one thing at a time or many? E.g.: one file at a time, multiple files to join/compare, a folder treated as one dataset, or auto-picking the right file from a library.
   - **When things go wrong** — what should it do when it can't answer confidently? E.g.: ask a clarifying question first, give a best guess and flag the uncertainty, show what it tried and where it got stuck, or retry a different approach automatically.

   **Skip any question Round 1 already answered.** Do not ask for information you already have. If an answer is vague, ask a follow-up before moving on.

---

### Round 3 — Feature depth (4 questions)

5. Read Rounds 1–2. This round uncovers what makes the agent genuinely powerful vs. a toy. Frame every question with idea-specific concrete examples — not abstract categories.
6. Ask **4 questions** covering these feature-depth dimensions:

   - **Analysis / reasoning depth** — how hard should it work on each request? E.g.: one fast LLM call, multi-step reasoning (try code, see result, try again), iterate until the right answer, or plan a full strategy before executing.
   - **Output richness** — what forms should results take? E.g.: plain text with key numbers, interactive charts, a summary table alongside the prose, an exportable file (CSV, cleaned dataset, report).
   - **Proactive intelligence** — should it do anything without being asked? E.g.: nothing, suggest follow-up questions, flag anomalies/data-quality issues it notices, auto-profile new data on upload.
   - **Integration surface** — what else does it connect to or produce for? E.g.: standalone, save results back to a library, export to Slack/email/dashboard, embed in an existing tool.

   **Skip any question if already answered.** Do not repeat covered ground.

---

### Round 4 — Constraints & scale (3 questions)

7. Read Rounds 1–3. This round surfaces hard constraints that would invalidate a design decision if missed. Give specific, concrete examples — not vague categories.
8. Ask **3 questions**:

   - **Data scale & performance** — how much data and how fast? E.g.: small files where latency doesn't matter, up to 100 MB with answers under 30s, millions of rows needing sampling/streaming, multiple concurrent users.
   - **Privacy & data residency** — where can data go? E.g.: everything stays on the machine/server (no cloud LLM calls), LLM calls OK but raw data rows never leave, cloud storage and APIs fine, or compliance requirements (SOC 2, GDPR, HIPAA).
   - **Reliability bar** — what's the quality/trust bar? E.g.: experimental prototype, production-ready decisions, an audit trail of what the agent did and why, access control per user.

---

### Round 5 — Observability, trust & transparency (3–4 questions)

9. Read Rounds 1–4. This round covers what users need to see in order to trust and debug the agent — often skipped but critical for agents that users depend on.
10. Ask **3–4 questions**:

    - **Reasoning visibility** — should users see how the agent reached its answer? E.g.: just the answer, the code it ran (collapsible), each step it tried, or the full reasoning chain.
    - **Usage & cost awareness** — should users see what the agent is spending? E.g.: hidden, tokens per query, estimated cost per query, a running daily total.
    - **Agent health & progress** — should users see the agent working? E.g.: a spinner, a step counter, a progress bar + timer, streamed partial answers.
    - **Logging & audit** — how much is recorded server-side? E.g.: nothing persistent, a query/answer log file, full run history in the database, a complete audit trail (who asked what, what code ran, what was stored).

---

### Additional product rounds (as many as needed)

After Round 5, check: *"Is there any dimension that would force spec-writer to guess?"* If yes, write another product round on that exact dimension — asking more questions is always preferred over guessing. Common dimensions that spill over:

- **Edge cases & error handling** — what happens when input is malformed, the LLM is wrong, an integration fails, or the user asks something outside scope?
- **Collaboration & sharing** — single user, shared team workspace, or multi-tenant with isolation?
- **Output lifecycle** — are results ephemeral (session-only) or persistent (saved, versioned, exportable)?
- **Onboarding & defaults** — first-run experience, example data, guided tours, sensible defaults vs. full configuration?
- **Specific feature trade-offs** — any remaining capability choice (e.g. "auto-profile on upload or on demand?", "clarification gate before every query or only on ambiguity?") that would produce a meaningfully different Phase 1.

Keep going until the brief you'll write in the synthesis step would let spec-writer fill every capability file without a single guess.

---

### Technical round — What do we need to build it? (3–4 questions, always last)

Read all prior rounds. Now ask the **technical build questions** — only genuine blockers, 3–4 total:
- **LLM provider** — offer **OpenRouter (primary/recommended — one key, any model)**, or direct **Anthropic**, **Gemini**, or **Other / self-hosted**. This drives which key the user sets. Default to OpenRouter when the user has no preference.
- **Stack preference** — language, database? ("No preference" → Python + SQLite defaults for local/prototype tools, PostgreSQL for production-grade, documented as assumptions.)
- **How will they access it?** — Web UI in a browser, CLI in the terminal, REST API, scheduled/automated job. Drives whether to build a frontend.
- **One follow-up** from prior rounds only if something would force a mid-build pause — skip if everything is clear.

**API key** (the only manual user step). Read `.env` and check whether the key for the chosen provider is already set (non-empty): `AGENT_OPENROUTER_API_KEY`, `AGENT_ANTHROPIC_API_KEY`, or `AGENT_GEMINI_API_KEY` (for **Other**, ask which env var + base URL). If present and non-empty, skip silently. Only if missing or empty, tell the user to set it in `.env` (from `.env.example`) and wait for confirmation. Never echo, print, paste, or commit a secret value.

**Synthesis brief**: write a **2–3 paragraph brief** covering: what the agent does and who uses it; the core interaction model (session shape, memory/state, multi-item handling); the key capabilities and features (analysis depth, output forms, proactive behaviours, edge-case handling, integrations, observability); the hard constraints (scale, privacy, reliability bar); and the technical stack and access model. Name the one core path for Phase 1 explicitly — the single most important thing a user does that proves the idea. ("Just build it" → narrow MVP, Python + SQLite defaults, OpenRouter provider, documented as assumptions.)

## Stage 2 — Design + scaffold + build Phase 1 (delegate)

Invoke the **agent-builder** sub-agent once with the brief and the populated `.env`. Tell it to run, in order, and return the **Phase-1 test-handoff**:

- **DESIGN** — spec-writer writes the full spec: vision/capabilities, `spec/architecture.md` (incl. the `## Stack` section), `spec/agent.md` (if a framework is chosen), and the phased plan in `spec/roadmap.md` under "## Phases of Development" (per phase: Goal · independent slices · key surfaces/files · the exact runnable Gate command · how the user tests it).
- **SCAFFOLD** — branch `feature/<slug>-v0.1` (slug must be unique — check `git branch -a` first and add a suffix if taken; see `harness/rules/git.md`), project dirs, `.env.example`, first commit + push, open the PR. Never commit on `main`.
- **BUILD PHASE 1** — fan out generators per independent slice in parallel, gate each slice with qa-auditor, then return the Phase-1 test-handoff and STOP.

Relay only the hard blockers it escalates (e.g. a required key still missing from `.env`).

## Stage 3 — Human testing gate (you own the human channel)

Phase 1 is the smallest working win: real on the one core path, with clearly-labelled non-functional stubs for everything coming later. **Spoon-feed the user: the ONLY things they should ever do by hand are (a) put secrets in `.env` and (b) interact with the running app (click / chat). They must never run a terminal command to test.** You own the gate, the server lifecycle, and re-invocation:

1. **Launch the server** (you own this — agent-builder does NOT start it; sub-agent background processes are cleaned up on return). The handoff includes the project root path + run command. In order from the project root:
   a. If the phase has a frontend slice: `cd frontend && npm run build && cd ..`
   b. If the phase has migrations: `alembic upgrade head`
   c. `venv/bin/python -m src` with `run_in_background: true`
   d. Health-check with retry: `for i in {1..10}; do curl -sf http://localhost:8001/health && break || sleep 2; done` — wait for the server before presenting the gate. If it never responds → route immediately to qa-auditor (boot failure), do not present the URL.
2. Present the handoff as **phase release notes**: the live URL, what was built this phase, what to click / type / look at, the expected result, which parts are clearly-labelled stubs vs real (a stub must never read as a bug), and what the next phase adds. No run commands in the handoff — the app is already serving.
3. Ask for the verdict as a **plain-text checklist question — never a single yes/no.** Hermes has no
   multi-select, so write the checklist INTO the question and ask the user to reply against each line,
   covering both load-state and one line per testable feature this phase shipped. E.g.:
   - *"Is the app loading at [URL]? Then, for each of these, tell me works / broken / didn't try:
     1) main view renders, 2) core action works, 3) output is correct, 4) feedback/hints work,
     5) streaming works."*
   A per-feature reply tells you *which* parts passed and *which* failed in one answer — a single
   verdict throws that away. If anything is unclear in their reply, ask a follow-up question. If the
   app didn't load or nothing worked, route to qa-auditor.
4. Route on their answers:
   - App didn't load → qa-auditor (boot failure), fix, re-present.
   - Any negative verdict → capture what they saw, then delegate to **zero-shot-fix** — pass the user's description, the phase context, the live URL, and any qa-auditor diagnosis already in context (file:line + SPEC/CODE classification) so it can skip re-diagnosis. It owns diagnose → fix → verify → commit + push autonomously, using the **scoped gate** for small CODE fixes (qa-auditor verifies only the changed surface + a real-key smoke call — not the full suite/E2E). When it returns VERIFIED, rebuild + restart the running app and **re-present** the gate. Loop until satisfied.
   - Positive only → ask in plain text: **"Ready for Phase 2, or is there one more thing to fix first?"** "One more thing" → route as negative above. "Yes" → Stage 4.

## Stage 4 — Per remaining phase (build → gate, repeat)

For EVERY remaining phase boundary:

1. Invoke **agent-builder** again — **one phase per invocation** — passing the user's feedback from the prior gate. It wires the relevant stubs into real functionality, fanning out generators per independent slice in parallel and gating each with qa-auditor, then returns that phase's test-handoff and STOPS.
2. Run the **Stage 3 human testing gate** again for this phase.

Repeat until no phases remain.

## Stage 5 — Ship + report

1. **qa-auditor** — final whole-tree drift audit (CLEAN). Route any divergence per Stage 3 and re-verify.
2. **agent-builder** — ensure the final state is pushed and the PR body is current.
3. Summarize for the user: what was built, the **live URL it's running at** (keep it serving), what's deferred, and the PR link. Run commands belong in the README for the record — not as something the user must execute to test.

## Adding a capability to an existing agent

If the spec is already filled in and the user is adding a capability: skip the scope intake; confirm the existing `.env` already holds the needed keys and ask only if the new capability requires a new provider/key. Tell agent-builder to run **spec-writer** (it owns architecture + roadmap now: add the capability to the spec and append an incremental phase to `spec/roadmap.md`, self-reviewed) → fan out the **frontend/backend generators** per slice → gate with qa-auditor. Then run the **human testing gate** on the new phase, same as any other.
