# Capability: Report Generate

## What It Does
Produce a downloadable PDF or Excel report from query results (and optionally chart images), with a UP Police–branded header, table of results, and the generated SQL for audit.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| result columns + rows | JSON | Agent pipeline (`sql_result`) | yes |
| NL answer | str | Agent pipeline (`answer`) | yes |
| generated_sql | str | Agent pipeline (`code_display`) | yes |
| format | str | User request or default `pdf` | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| file_url | str | `/assets/reports/<id>.pdf` or `.xlsx` |
| file_size | int | API response |
| download button | UI | Chat bubble with download link |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| reportlab / openpyxl | Write PDF or XLSX to `./assets/reports/` | Omit download links; NL answer still shown; log failure |

## Business Rules

- Default format is PDF; Excel offered when user explicitly asks (or rows > 500).
- PDF header includes: agent name, session ID, query timestamp, user ID.
- Report contains: NL answer, data table, generated SQL, data source attribution.
- Reports are stored for 30 days, then auto-deleted.

## Success Criteria

- [ ] Click "Download PDF" → PDF opens with answer, table, SQL, header
- [ ] Click "Download Excel" → `.xlsx` opens with same sections
- [ ] LLM failure mid-report → report omitted, NL answer still returned, no 500
