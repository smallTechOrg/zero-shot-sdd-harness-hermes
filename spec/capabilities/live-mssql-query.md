# Capability: Live MsSQL Query

## What It Does

Connect to a live read-only MsSQL database, reflect relevant schema, generate and validate SQL from a natural-language question, execute it within strict row/time budgets, return structured results, and cache results by query fingerprint so repeated asks are cheap and do not hammer the DB.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Connection label / config | JSON / env-backed settings | analyst UI or `.env` | yes |
| Analyst question | text | analyst UI | yes |
| Schema allowlist | config | deployment | yes |
| Row cap | integer | config default | no |
| Query timeout seconds | integer | config default | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Natural-language answer | text | API + UI |
| Result table payload | JSON | API + UI |
| Generated SQL | text | UI with copy action |
| Query fingerprint / cache indicator | text | UI + log |
| Row count / latency metadata | JSON | API + UI |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| MsSQL via pyodbc | Schema reflection, safe read-only SELECT execution | Retry with backoff; abort and surface connection/schema error |
| LLM | SQL drafting in constrained JSON/schema; answer synthesis | Retry with backoff; never fall back to guesswork |
| Local cache store | Fingerprint → result rows + metadata | Treat as cache miss and re-query the DB |
| SQLite app DB | Persist run metadata | Log and continue without persistence |

## Business Rules

- All queries must be read-only; write/DDL is never emitted by the agent.
- Generated SQL is validated for allowlisted schemas/tables and rejected before execution if outside scope.
- Row cap and timeout are enforced by the runner, not only the DB side.
- Repeated identical questions reuse cached results by default and clearly label cache hits.
- Query text, analyst identity, latency, row count, and provider/model are persisted for audit.
- The connection config must not be exposed in logs or responses.

## Success Criteria

- [ ] A schema browser UI surfaces tables and columns relevant to the analyst’s question.
- [ ] Generated SQL is shown before execution and is syntactically valid.
- [ ] Execution completes within the configured timeout and row cap.
- [ ] A repeated identical question returns from cache and labels it as a cache hit.
- [ ] The UI shows latency, row count, and cache state for every DB-backed answer.
