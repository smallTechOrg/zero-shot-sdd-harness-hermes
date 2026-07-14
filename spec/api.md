# API — Data Analyst Agent

Base: `http://localhost:8001`

## POST /api/query
Body: `{ "question": "..." }`
Returns:
```json
{
  "runId": "guid",
  "plan": "short analysis plan",
  "chartType": "bar|line|pie",
  "sql": "SELECT TOP 1000 ...",
  "reasoningSteps": ["...", "..."],
  "clarification": null,
  "data": { "labels": [...], "datasets": [{ "label": "...", "data": [...] }] },
  "auditSaved": true
}
```
If clarification needed: `clarification` is a string, `data` is null, no SQL runs.

## POST /api/query/stream  (SSE)
Body: `{ "question": "..." }`
Streams `text/event-stream` events: `plan`, `sql`, `step` (each reasoning step
with "Step N of M"), `data`, `done`. Terminal `done` carries the runId.

## GET /api/schema
Returns cached warehouse schema + aggregate profiles JSON.

## GET /api/audit?date=YYYY-MM-DD
Returns `{ date, runs: [...], totalTokens }` for the running daily token total.

## GET /api/health
Returns `{ "status": "ok" }`.

## Error contract
Deny-list violation → 400 `{ error: "SQL rejected: contains <TOKEN>" }`.
Missing OpenRouter key → 503 `{ error: "LLM not configured" }` (build/test unaffected).
