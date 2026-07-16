# CCTNS Analyst — spec

This is the spec directory for the CCTNS analyst agent being built under
`/zero-shot-build` on this repo. The spec is the source of truth — when
code and spec disagree, the spec wins (`/zero-shot-sync`).

## Manifest (read in order)

```
spec/roadmap.md              ← what + how (phases, slices, gates)
spec/architecture.md         ← system architecture + Stack
spec/agent.md                ← LangGraph state machine (REQUIRED — LangGraph in use)
spec/capabilities/           ← one file per capability
spec/data.md                 ← entities we own (AnswerRun, CctnsTable)
spec/api.md                  ← POST /v1/answer, GET /health, static /app
spec/ui.md                   ← single Next.js page at /app/
```
