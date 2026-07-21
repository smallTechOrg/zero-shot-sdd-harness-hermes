# Capabilities Index

> **Boilerplate status:** Complete for the UP Police Data Analyst agent. Each file describes exactly one discrete capability; product-side design docs are in `spec/roadmap.md` and `spec/architecture.md`.

---

## What Is a Capability?

A capability is a single, discrete action or behaviour the agent performs. Examples:
- "Answer a natural-language question over uploaded CSV exports"
- "Return a downloadable CSV plus generated SQL for the same question"
- "Serve the same question from a local cache when the live DB is unreachable"

## Capabilities in This Project

| Capability | File |
|------------|------|
| Analyse structured police data (CSV + live DB, cache fallback) | [analyse_data.md](analyse_data.md) |

## Capability File Template

Each capability file answers:
- **What it does** (one sentence)
- **Inputs** (what data it receives)
- **Outputs** (what it produces)
- **External calls** (APIs, LLMs, databases it touches)
- **Error cases** (what can go wrong and how it's handled)
- **Success criteria** (how we test it)
