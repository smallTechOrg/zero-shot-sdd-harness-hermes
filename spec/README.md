# Spec — Single Source of Truth

This directory is the authoritative specification for this project. All code must match this spec. When spec and code disagree, spec wins — fix the code.

## Status

`spec/roadmap.md` is complete. The current agent is a **data analysis agent** for CSV/JSON natural-language Q&A with insight summaries and chart specs.

## Structure

`spec/` is **the product** — what the agent does, in terms a user can read and edit. Generic engineering doctrine (how to build anything) lives in `harness/`.

```
spec/                 ← The product (you read & edit this)
  roadmap.md       ← Purpose, goals, success criteria, future phases
  architecture.md  ← System design, layers, data flow, and the chosen ## Stack
  agent.md         ← This agent's graph (state, nodes, edges) — if a framework is used
  data.md          ← Data schema
  api.md           ← API surface (REST/GraphQL/CLI/etc.)
  ui.md            ← UI requirements (if any)
  capabilities/    ← One file per discrete capability
```

## Governance Rules

1. **Spec first** — no code change without a spec backing it
2. **One fact, one place** — never duplicate facts across spec files; cross-reference with links
3. **Capabilities are atomic** — each file in `capabilities/` describes exactly one discrete thing the agent can do
4. **No implementation details in product spec** — `spec/` describes WHAT, `harness/` describes HOW
5. **Update spec before code** — if requirements change, update the spec first, then update the code

## Who Updates the Spec

- **New project:** the `/zero-shot-build` skill drives the spec-writer sub-agent, which drafts and self-reviews the spec
- **New capability:** run `/zero-shot-build` on an existing spec — it adds the capability via the spec-writer
- **Drift between spec and code:** run `/zero-shot-sync` to reconcile (spec wins)
