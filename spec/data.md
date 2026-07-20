# Data Model

## Storage Technology
Microsoft SQL Server (MSSQL) is used as the source of truth for all police data (FIR/CCTNS, HR/personnel, logistics/property). The agent connects to a read-only database user with permissions to SELECT from the relevant schemas. An audit table is added to log all queries for compliance.

## Entities
### Entity: AuditLog
Purpose: Immutable record of every analyst query for audit and compliance (PVP/IT Act).
|| Field | Type | Required | Description ||
|-------|------|----------|-------------||
| id | BIGINT IDENTITY(1,1) | yes | Primary key ||
| officer_id | VARCHAR(50) | yes | Identifier of the officer who made the request (from header or auth) ||
| question_text | TEXT | yes | The natural-language question posed by the officer ||
| refined_question | TEXT | no | The question after any clarification steps (if applicable) ||
| executed_sql | TEXT | yes | The SQL query that was run against the database ||
| row_count | INT | yes | Number of rows returned by the query ||
| execution_time_ms | INT | yes | Time taken to execute the SQL query (in milliseconds) ||
| result_hash | CHAR(64) | yes | SHA-256 hash of the query result (for tamper evidence) ||
| llm_model_used | VARCHAR(50) | yes | The LLM model that generated the SQL (e.g., "anthropic/claude-sonnet-3.5") ||
| llm_prompt_tokens | INT | yes | Number of prompt tokens sent to the LLM ||
| llm_completion_tokens | INT | yes | Number of completion tokens returned by the LLM ||
| status | VARCHAR(20) | yes | Outcome: "success", "clarification_needed", "error" ||
| error_message | TEXT | no | If status is "error", the error message from the agent ||
| created_at | DATETIME2(3) | yes | Timestamp when the query was received (UTC) ||
| completed_at | DATETIME2(3) | no | Timestamp when the query finished processing ||

### Entity: OfficerReport
Purpose: Stores pinned (saved) reports for officers to reuse quickly.
|| Field | Type | Required | Description ||
|-------|------|----------|-------------||
| id | UNIQUEIDENTIFIER | yes | Primary key (NEWID()) ||
| officer_id | VARCHAR(50) | yes | Identifier of the officer who pinned the report ||
| question_text | TEXT | yes | The natural-language question that was pinned ||
| answer_text | TEXT | yes | The answer generated at the time of pinning (for quick view) ||
| pinned_at | DATETIME2(3) | yes | Timestamp when the report was pinned ||
| expires_at | DATETIME2(3) | no | Optional expiry for temporary pins (null = permanent) ||

## Relationships
- AuditLog.officer_id references OfficerReport.officer_id (logical; no FK as officer info may come from external auth).
- One officer can have many audit log entries and many pinned reports.

## Data Lifecycle
- **AuditLog**: Insert-only; rows are never updated or deleted. Partitioning by month/year may be applied for performance in production.
- **OfficerReport**: Insert when a user pins a report; update if the user refreshes the pin (e.g., with new data); delete when the user unpins or when expires_at is passed (cleanup job).

## Sensitive Data
The agent is designed to **never** store or transmit raw row data from the protected tables (FIR, HR, logistics). The AuditLog stores only:
- Aggregates (row count, execution time)
- A hash of the result set (for tamper evidence, not reconstruction)
- The SQL query (which is read-only and parameterized)

Fields that contain PII (e.g., victim names, addresses, officer personal details) are **never** included in LLM prompts, logs, or API responses beyond what is strictly necessary for the aggregate answer. The database user used by the agent has SELECT access only to the necessary views/tables, and row-level security (to be added in Phase 3) will further restrict data to the officer's jurisdiction.

All logs (application and audit) avoid storing raw PII; any error messages that might contain data are sanitized before logging.