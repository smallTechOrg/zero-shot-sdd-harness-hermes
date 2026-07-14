# Capability: nl-to-chart

Turn a plain-English question into a read-only SQL query and a Chart.js chart.

## Inputs
- `question` (string) — plain-English analytics ask.
- Cached warehouse schema + aggregate profiles (server-side context).

## Steps
1. Plan the analysis + choose chart type (LLM).
2. Generate read-only SQL with enforced TOP (LLM, JSON contract).
3. Validate (deny-list + TOP + no SELECT *).
4. Execute read-only; shape rows into Chart.js data.
5. Audit the run.

## Outputs
- `{ plan, chartType, sql, reasoningSteps, clarification?, data?, auditSaved }`.

## Guarantees
- Raw rows never sent to LLM.
- Mutating SQL rejected before execution.
