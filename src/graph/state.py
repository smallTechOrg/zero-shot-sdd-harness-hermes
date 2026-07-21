"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
 run_id: str
 input_text: str
 instruction: str
 output_text: str
 provider: str
 model: str
 status: str
 error: str | None
 question: str
 schema_summary: str | None
 data_source: str | None
 row_limit: int | None
 csv_file_ids: list[int] | None
 memory_context: str | None
 saved_workspace_id: int | None
 query_plan: dict | None
 tables_touched: list[str] | None
 generated_code: str | None
 executed_sql: str | None
 executed_rows: list[dict] | None
 executed_columns: list[str] | None
 executed_row_count: int | None
 latency_ms: int | None
 result_table: dict | None
 answer_text: str | None
 followups: list[str] | None
 anomaly_flags: list[str] | None
 sensitive_warning: str | None
 token_usage: dict | None
