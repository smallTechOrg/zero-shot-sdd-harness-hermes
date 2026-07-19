---
name: zero-shot-build
description: Turn a zero-shot idea into a perfectly-working, thoroughly-tested, spec-driven agent. One deep intake (which also collects the API keys into .env), then the ROOT SESSION orchestrates the build one phase at a time — autonomous within a phase, with a human testing gate between phases. Also used to add a new capability to an existing agent.
argument-hint: [your idea]
disable-model-invocation: true
allowed-tools: Bash(git*) Bash(gh*) Bash(uv*)
---

# zero-shot-build — the Hermes build loop

**You are the ROOT SESSION and you are the orchestrator.** On Hermes there is no delegated
"agent-builder" running the build for you: delegated workers cannot spawn their own workers
(`max_spawn_depth=1`), cannot talk to the user, and their background processes are killed the
moment they return. Everything that needs the user, git, or a long-lived server therefore
lives HERE, in the root session. You delegate *leaf work* (spec-writing, one code slice, one
audit) to the specialist roles in `harness/agents/` — via `delegate_task` when it is
available, **inline otherwise** — and you verify every handback yourself.

The idea is in `$ARGUMENTS`. **If `$ARGUMENTS` is empty, ask the user in plain text to
describe their idea and WAIT for their free-text reply.** Never use `clarify` to solicit or
suggest the idea itself — the idea must come from the user as their own text.

Goal: **one prompt → a perfectly-working, thoroughly-tested agent, one user-testable phase
at a time.**

## The execution model (read this before anything else)

| Concern | Owner | Why |
|---|---|---|
| Talking to the user (`clarify`, gates, blockers) | **Root session only** | workers cannot own the human channel |
| git / branch / PR / commit+push | **Root session only** | workers may return early; git must never be half-done |
| Server lifecycle (boot, smoke, keep serving) | **Root session only** | a worker's background processes die when it returns |
| Writing the spec | spec-writer role | single design authority, self-reviewed |
| Implementing one slice + its tests | code-generator role (one per slice) | parallel when delegation works, sequential inline otherwise |
| Independent review + running gates | qa-auditor role | read-only checker, never the author |

**Delegation policy — try, verify, fall back inline:**

1. **Try** `delegate_task` for each specialist role (name the role file; up to 3 children in
   parallel for independent slices).
2. **Verify every handback.** A worker's summary is advisory, not evidence. On return: check
   the durable files actually exist, re-run its gate command cheaply (`py_compile`,
   `pytest --collect-only`, or the real gate if logic changed), confirm it committed nothing
   (git is yours). A worker that returned at "95% done" is normal — **you finish the
   remainder inline**; never re-delegate the same 5%.
3. **Fall back inline.** If delegation is unavailable, errors out, or stalls: read the role
   file (`harness/agents/<role>.md`) and execute it yourself as a checklist, in the same
   order the delegated version would run. The build NEVER stalls waiting for a worker that
   cannot spawn. Inline is the *normal* mode on constrained Hermes configs, not a failure.

**The inner loop (per slice — this is the engine):**

```
implement → run the REAL gate → READ the actual output → fix → re-run
```

Never claim, always observe: a gate "passes" only when you ran the exact command and read
its real output tail this session. Cheap re-verification (`py_compile` + collect-only) after
mechanical edits; the full real-key gate after logic changes and before any handoff.

## Stage 1 — Intake (the only interactive setup step)

Intake has **two fixed sections and a variable middle**:

1. **Product rounds (variable, minimum 5)** — all product questions, progressively deeper.
   Keep going until every dimension that would force a design decision in Phase 1 is
   resolved. Five rounds is the floor; complex ideas may need more. Each round covers a
   different dimension and never repeats covered ground.
2. **Technical round (fixed, always last)** — build-blockers only (LLM provider, stack,
   access method).

All rounds use `clarify`. Two resilience rules:

- **If `clarify` doesn't load** (it can fail on a plain command line), ask the questions in
  plain text **one by one** — ask one, wait for the reply, then ask the next. Never dump all
  questions in a single message.
- **Follow up on ambiguity.** If an answer could be read two ways, or a single pick may have
  dropped options that also apply, ask a short follow-up — never guess.
- **Empty answer = "you decide".** Pick the lowest-risk default, record it as
  `Assumed: …` in the brief, and move on. Don't re-ask, don't block.

**How to decide when to stop product rounds:** after each round ask: *"Is there any
dimension — interaction model, state/memory, features, constraints, edge cases,
observability, integrations — that, if left unresolved, would force spec-writer to guess?"*
If yes: another round on that dimension. If no: technical round. Err toward one more round
rather than an ambiguous brief.

**The golden rule: Phase 1 is the smallest user-testable quick win.** Richer intake sharpens
*which* slice to build first — it does not license a bigger Phase 1.

**The cardinal rule across ALL rounds: every question and every option must be specific to
THIS idea.** After Round 1 you know the idea category — use it. A user must instantly
recognise every option as being about their thing. Generic options are a failure.

### Round 1 — What is the idea? (4 questions, all multiSelect)

Acknowledge the idea in one sentence, then ask four themes — adapt wording and all options
to the idea:

- **What it works on** *(4 idea-specific options)* — the data, content, or domain it
  processes. Concrete: not "documents" but "CSV exports from our CRM".
- **What it produces** *(4 idea-specific options)* — concrete outputs: "an interactive chart
  I can explore", "a ranked list with reasons".
- **Usage pattern** — who uses it, how often, in what context.
- **Non-negotiables** — always offer at least: "My data can't leave my machine", "Keep costs
  very low", "Must connect to [something they mentioned]", "None — just build it well".

### Round 2 — How users interact (4 questions, all multiSelect)

Write ALL questions and options as a product designer who has used tools exactly like this:

- **Session model** — how long does one "conversation" last?
- **Memory & state** — what carries across turns or sessions?
- **Multi-item handling** — one thing at a time or many?
- **When things go wrong** — clarify first, best-guess + flag, show the attempt, retry?

Skip any question Round 1 already answered.

### Round 3 — Feature depth (4 questions, all multiSelect)

What makes it genuinely powerful vs a toy — all options idea-specific concrete features:

- **Analysis / reasoning depth** — one LLM call? multi-step? iterate-until-right? plan-first?
- **Output richness** — text, charts, tables, exportable files?
- **Proactive intelligence** — only answers? suggests follow-ups? flags anomalies?
- **Integration surface** — standalone, saves back, exports, embeds?

### Round 4 — Constraints & scale (3 questions, all multiSelect)

- **Data scale & performance** — how much data, how fast?
- **Privacy & data residency** — local-only, rows-never-leave, cloud-fine, compliance?
- **Reliability bar** — prototype, production, audit trail, access control?

### Round 5 — Observability, trust & transparency (3–4 questions, all multiSelect)

- **Reasoning visibility** — answer only, show the code, show every step, full chain?
- **Usage & cost awareness** — hidden, tokens, cost per query, running total?
- **Agent health & progress** — spinner, step counter, progress + timer, streaming?
- **Logging & audit** — nothing, per-query log, full DB history, full audit trail?

### Additional product rounds (as many as needed)

Common spill-over dimensions: edge cases & error handling; collaboration & sharing; output
lifecycle (ephemeral vs persistent); onboarding & defaults; any remaining trade-off that
would produce a meaningfully different Phase 1. Keep going until the brief would let
spec-writer fill every capability file without a single guess.

### Technical round — always last (3–4 questions)

- **LLM provider** *(single-select)* — **Anthropic**, **Gemini**, **OpenRouter (any
  model)**, **Other / self-hosted**. Drives which key the user sets. (The baseline's
  provider layer supports all three out of the box.)
- **Stack preference** — language, database? ("No preference" → the baseline stack: Python +
  FastAPI + LangGraph + SQLite for local tools, PostgreSQL for production-grade — documented
  as assumptions.)
- **How will they access it?** — Web UI, CLI, REST API, scheduled job.
- **One follow-up** only if something would force a mid-build pause.

**API key** (the only manual user step). **`.env` is a secret-bearing file — Hermes's
`read_file` tool hard-blocks it outright ("Access denied: ... secret-bearing environment
file"). Never call `read_file` on `.env` — a live run hit this and, instead of working
around it, asked the user to manually open the file and confirm, 10 minutes into intake.**
Instead run a `terminal`/`execute_code` script that loads `.env` itself (`python-dotenv`,
or `source .env` in bash) and prints ONLY a pass/fail signal — presence as a boolean for
the chosen provider's var (`AGENT_ANTHROPIC_API_KEY`, `AGENT_GEMINI_API_KEY`,
`AGENT_OPENROUTER_API_KEY`; for **Other**, ask which env var + base URL) — never the value
itself. **Use an ABSOLUTE path to `.env`, never a relative one.** `execute_code` runs the
script in its own sandboxed process, not the repo's working directory — `dotenv_values(".env")`
resolves against the sandbox and silently reports MISSING even when the key is genuinely
present in the repo (confirmed on a live run: the key was present, the relative-path script
still said MISSING). Resolve the repo root first (e.g. from a known file's path, or have the
`terminal` tool `pwd`/`git rev-parse --show-toplevel` and pass that in), then
`dotenv_values(f"{repo_root}/.env")`. Present → **validate it works** in that same script: one minimal real API call
(e.g. the provider's cheapest endpoint), printing only `OK` or the error type
(`401`/`429`/`model_not_found`) — a key can be *present but dead* (revoked account, expired
trial, dead model slug), and discovering that mid-build wastes a phase. Missing, or the test
call fails → tell the user the specific reason and ask them to fix `.env` (from
`.env.example`), then re-run the check. Never echo, print, or commit a key value.

**Synthesis brief**: 2–3 paragraphs covering: what the agent does and who uses it; the
interaction model (session shape, memory, multi-item); key capabilities (depth, outputs,
proactive behaviours, edge-case handling, integrations, observability); hard constraints
(scale, privacy, reliability); stack + access model. Name the one core path for Phase 1
explicitly. ("Just build it" → narrow MVP, baseline defaults, documented as assumptions.)

## Stage 2 — Design + scaffold (first phase only)

1. **DESIGN** — run the **spec-writer** role (delegate or inline) with the brief. It writes
   the full spec: capabilities, `spec/architecture.md` (incl. `## Stack`), `spec/agent.md`
   (the agent graph — REQUIRED when a framework is chosen; pick patterns from
   `harness/patterns/agentic-ai.md`), and the phased plan in `spec/roadmap.md` (per phase:
   Goal · independent slices · key files · the exact runnable Gate command · how the user
   tests it). **Verify on handback**: no `<!-- FILL IN -->` left, every phase has a runnable
   gate, `spec/agent.md` exists if a framework is chosen. Surface its `Assumed:` flags to
   the user in your next message (don't wait on them).
2. **SCAFFOLD** — you own git (`harness/rules/git.md`):
   - **Clean-baseline precheck (do this FIRST).** A fresh build must start from untouched
     boilerplate: confirm `spec/` still has `<!-- FILL IN -->` markers AND no app/agent
     output dir already exists. If either is already populated, you are on a PRIOR build's
     branch — STOP and confirm with the user before continuing. (A live run inherited an old
     ASP.NET+MSSQL data-analyst spec this way and tried `dotnet`/Docker on a Python box.)
   - `base=$(git rev-parse --abbrev-ref HEAD)` — capture `<base>` BEFORE branching; never
     `git checkout main` first (you dogfood the harness version you are on).
   - `name="feature/<slug>-$(date +%Y%m%d-%H%M)-v0.1"` — the date-time slug makes it unique.
     Before creating it, `git ls-remote --heads origin "$name"`; if it somehow exists, bump
     the timestamp. **Never `git checkout` an existing feature branch to build into** — that
     imports the prior build's stack. Then `git checkout -b "$name"`.
   - The baseline in `src/` IS the scaffold — generators extend it in place (rename the
     capability slot, never copy beside it). Update `.env.example` for any new env vars.
   - First commit + push, then open the PR immediately: `gh pr create --base "$base"` —
     **never `--base main`**. `main` is boilerplate-only, ABSOLUTELY.

## Stage 3 — Build one phase (the loop)

For the current phase (Phase 1 first; later phases on user approval):

1. **Read the phase's slices** from `spec/roadmap.md`.
2. **Implement each slice** via the **code-generator** role — delegate independent slices in
   parallel (up to 3) when `delegate_task` works AND the LLM key is a paid/dedicated one;
   otherwise inline, sequentially, one slice at a time. **On a shared/free key, prefer
   sequential inline** — parallel fan-out multiplies 429s on one credential pool and stalls
   the build (mining the prior runs showed ~14h cumulative blocked on pool exhaustion).
   Verify each handback's CONTENT, not just its status — a worker can return
   `status=completed` whose body is a rate-limit error; that slice is NOT done. Each slice = its surfaces + its tests, test-first. Tell each generator exactly
   which files it owns; slices own disjoint paths.
3. **Gate each slice as it lands** via the **qa-auditor** role (delegate or inline):
   independent code review + run the slice's real gate (real LLM/API keys from `.env`, prod
   DB driver) + read the actual output. BLOCKED → route the named finding back to the
   generator role for that surface; loop until VERIFIED. Never start the next phase with a
   BLOCKED slice.
4. **Phase-level checks (once per phase, after slices aggregate):**
   - **Boot gate**: start the app with the EXACT documented run command from the repo root
     (pin the interpreter: `.venv/bin/python -m src` — never bare `python`; a shared agent
     venv can shadow it). No ImportError/startup traceback. Green pytest does NOT prove
     this — pytest's `sys.path` masks `src.`-import bugs.
   - **Fresh-DB check**: if the schema changed this phase, `uv run alembic upgrade head`
     (and `alembic current` shows a revision) — or, pre-migrations, delete/recreate the dev
     SQLite file. A stale dev DB turns a green suite into a 500 on the live server.
   - **Live smoke**: health + the phase's new endpoint(s) + the UI page served — real
     responses read, not assumed.
5. **Commit + push the phase** — stage the phase's files explicitly (never `git add -A`),
   `git commit -m "phase-N: <desc>" && git push origin <branch>` as ONE atomic action.
   Update the PR body (what this phase added, how to run, what's deferred). **Hard gate: a
   phase isn't done until committed + pushed + PR current — do this BEFORE the handoff.**

## Stage 4 — Human testing gate (you own the run)

**The user's ONLY jobs are: (a) put secrets in `.env`, (b) click around the running app.
They never run a terminal command to test.** You own the server and the gate:

1. **Launch the server yourself**: from the repo root, `.venv/bin/python -m src` using the
   terminal tool's **background flag** (`background=true` / `run_in_background`) on a **free
   port** (retry the next port if busy; export `PORT`). **Never a `&`-backgrounded command,
   `nohup`, `setsid`, or `disown`** — Hermes hard-blocks those and points you to the
   background flag; the readiness watch fires on the framework's startup line (e.g. uvicorn
   "Application startup complete"). Then, in a FOLLOW-UP terminal call, health-check with
   retry: `for i in {1..10}; do curl -sf localhost:$PORT/health && break || sleep 2; done`
   (each terminal call starts fresh at repo root — use absolute paths, don't rely on a prior
   `cd`). This curl/httpx smoke asserting response CONTENT is the gate of record; a browser
   check is a bonus only when the browser tool is actually available. If it never responds →
   BLOCKER: route to qa-auditor, fix, relaunch. **Never present a URL you haven't verified
   live this session; never hand the user a command to run the server.**
2. **Present phase release notes**: the ONE live URL; what was built this phase; what to
   click/type; the expected result; which parts are clearly-labelled stubs vs real (a stub
   must never read as a bug); what the next phase adds. No terminal commands in the handoff.
3. **Ask via `clarify` — ALWAYS MULTI-SELECT, never a single verdict.** One option per
   testable feature this phase shipped, plus "App didn't load / error" and "Nothing worked"
   escapes. A multi-select tells you *which* parts passed in one answer. If `clarify` won't
   load: plain text, one question at a time.
4. **Route on the answer:**
   - Didn't load → qa-auditor (boot failure) → fix → relaunch → re-present.
   - Any negative → capture what they saw → run the **zero-shot-fix** procedure (you stay
     the orchestrator; qa-auditor diagnoses + classifies SPEC-vs-CODE, the generator fixes,
     scoped re-gate) → rebuild/restart → re-present. Loop until satisfied.
   - All positive → *"Ready for Phase N+1?"* — on "one more thing first", route as negative;
     on yes → Stage 3 for the next phase.

## The build journal (capture learnings as you go)

Maintain **`NOTES.md` on the build's feature branch** throughout the run — commit it with
each phase. It is a *harness-improvement log*, not an app changelog: record only friction
with the harness or the runtime, each entry with symptom → what you did → the durable
lesson. Typical entries: a `clarify` load failure, a delegated worker that returned early,
a gate that passed for the wrong reason, a rule that fought you, a question the intake
should have asked. Timestamp the run start (date + time) in the first entry — it lets the
Hermes execution logs (`~/.hermes/logs/agent.log`, `~/.hermes/sessions/request_dump_*`)
be sliced to this run afterwards.

After the run, durable generic lessons get distilled into
`references/hermes-pitfalls.md` (and role files where they change behaviour) via a
separate harness PR; the war-story details stay behind on the build branch's NOTES.md.

## Stage 5 — Ship + report

1. **qa-auditor** — final whole-tree drift audit (CLEAN). Route divergences as in Stage 4.
2. Ensure everything is pushed and the PR body is current. Never merge the PR yourself.
3. Summarize: what was built, the **live URL it's serving at** (keep it running), what's
   deferred, the PR link. Run commands live in the README for the record — not as something
   the user must execute.

## Adding a capability to an existing agent

Spec already filled in → skip scope intake; confirm `.env` covers any new provider/key.
spec-writer adds the capability + an incremental phase to `spec/roadmap.md` (self-reviewed)
→ Stage 3 loop for that phase → Stage 4 gate. Same rules, one phase.

## Failure modes (each of these happened on a real run)

- Waiting for a delegated worker that can never spawn (depth cap) instead of going inline.
- Trusting a worker's "done" without checking the files / re-running the gate — workers
  return early at ~95% routinely; the root finishes.
- A worker (or you) launching the test server inside a delegate — it dies on return; only
  the root serves.
- Presenting the gate without a live, verified URL — bouncing an un-run app back to the
  user as a question. The gate owns the run.
- Bare `python`/`uvicorn` picking up the wrong venv → phantom `ModuleNotFoundError`. Always
  `.venv/bin/python -m src`.
- A stale dev DB (schema drifted since create_all) turning green tests into live 500s —
  migrate or recreate before the boot gate.
- Looping an LLM call per output line/token in generated code — one batched call per
  artifact, split downstream (a per-line loop burned a real monthly spend cap).
- Single-choice gate questions (throws away per-feature signal); dumping all intake
  questions in one message when `clarify` is down.
- Committing to `main`, a commit without a push, a push without a PR, `git add -A`, or
  staging `.env`.
