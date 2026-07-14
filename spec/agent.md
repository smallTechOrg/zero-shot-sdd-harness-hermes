# Agent Flow — Data Analyst Agent

## Graph (single-turn, plan-then-act)

```
question
   │
   ▼
[schema+profile load]  ← cached; INFORMATION_SCHEMA + sampled aggregates
   │  (schema + profile stats ONLY — no raw rows)
   ▼
[LLM: plan + chartType + sql + reasoning + clarification?]  (OpenRouter, JSON contract)
   │
   ├── clarification present ──▶ return clarification to UI (STOP, no SQL)
   │
   ▼
[validate SQL]  deny-list (INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/GRANT/EXEC/MERGE)
   │            + enforce TOP row limit + reject SELECT *
   ▼
[execute read-only]  Microsoft.Data.SqlClient
   │  (rows → ChartService ONLY, never back to LLM)
   ▼
[shape chart]  {labels, datasets}
   │
   ▼
[audit]  SQLite: question, plan, sql, chartType, rowCount, tokens, ts, outcome
   │
   ▼
stream: plan → sql → steps → data → done
```

## LLM Output Contract (strict JSON)

```json
{ "plan": "...", "chartType": "bar|line|pie", "sql": "SELECT TOP N ...",
  "reasoning": ["step 1", "step 2"], "clarification": null }
```

## Proactivity
- Auto-profile: first time a table is queried, its sampled aggregate profile is
  computed and cached; included in the prompt.
- Data-quality flags: null% / outlier notes surfaced in the reasoning text.

## Safety Invariants
- Raw rows never enter an LLM request (enforced by construction).
- No query executes without passing the deny-list + TOP check.
