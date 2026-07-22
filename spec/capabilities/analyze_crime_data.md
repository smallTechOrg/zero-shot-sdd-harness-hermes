# Capability: Analyze Crime Data
## What It Does
Accepts a natural language query regarding uploaded crime CSV datasets and returns a structured analysis including summaries, charts, and recommendations based on Pandas aggregations.
## Inputs
| Input | Type | Source | Required |
|---|---|---|---|
| session_id | string | API Request | Yes |
| query | string | API Request | Yes |
## Outputs
| Output | Type | Destination |
|---|---|---|
| structured_dashboard | JSON | API Response |
## External Calls
| System | Operation | On Failure |
|---|---|---|
| Gemini LLM | Intent Parsing / Pandas Gen | Retry 2x, then return error message |
| Gemini LLM | Synthesis | Return raw data error |
## Business Rules
- Must dynamically inspect CSV schemas attached to the session.
- Cannot delete or modify CSV files during analysis (read-only Pandas ops).
## Success Criteria
- [ ] Querying "highest crime district" generates Pandas code that groups by district, sorts, and correctly synthesizes the top result.
