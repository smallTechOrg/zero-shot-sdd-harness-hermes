# Capability: pin_report
## What It Does
Allows an officer to save a question and its result (or a link to re-run it) for quick access later, pinned to their sidebar.

## Inputs
| Input | Type | Source | Required |
|-------|------|--------|----------|
| question | string | from a prior ask_question turn | yes |
| officer_id | string | header or auth | yes |
| nickname | string | user-defined label for the pin | no |

## Outputs
| Output | Type | Destination |
|--------|------|-------------|
| pin_id | integer | returned to frontend |
| nickname | string | displayed in sidebar |
| pinned_at | timestamp | stored in database |
| status | string | "success" or "error" |

## External Calls
| System | Operation | On Failure |
|--------|-----------|------------|
| OfficerReport table | INSERT or UPDATE | set error, return error response |
| AuditLog table | INSERT (pin event) | log error but do not fail pin |

## Business Rules
- A pinned report stores the original question (not the result set) so it can be re-run against fresh data.
- Officers can pin the same question multiple times with different nicknames.
- Pinned reports are private to the officer unless sharing is enabled (Phase 2+).
- The pin does not store the result set to avoid stale data; re-running gets current data.
- Each pin action is logged in the audit trail for accountability.

## Success Criteria
- [ ] After a successful ask_question, the officer can click a pin icon to save the query.
- [ ] The pinned query appears in the sidebar under "Pinned" with the given nickname (or a default).
- [ ] Clicking the pinned query re-runs the question and displays the current result.
- [ ] The audit log records the pin action with officer_id and question.
- [ ] Pins persist across page refreshes and sessions.