"""Domain models — CSV analyst request/response shapes."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CSVUploadResponse(BaseModel):
 file_id: int
 file_name: str
 row_count: int
 columns: list[str]
 schema_fingerprint: str


class CSVQueryRequest(BaseModel):
 question: str = Field(..., min_length=1, max_length=2000)
 data_source: str = Field(default="csv", pattern="^(csv|live_db|cache)$")
 csv_file_ids: list[int] | None = None
 workspace_id: int | None = None
 row_limit: int | None = Field(default=None, ge=1, le=1_000_000)


class CSVQueryResponse(BaseModel):
 run_id: str | int
 status: str
 answer_text: str | None = None
 result_table: dict | None = None
 generated_sql: str | None = None
 tables_touched: list[str] | None = None
 executed_row_count: int | None = None
 latency_ms: int | None = None
 provider: str | None = None
 model: str | None = None
 csv_download_url: str | None = None
 followups: list[str] | None = None
 anomaly_flags: list[str] | None = None
 sensitive_warning: str | None = None
 served_from_cache: bool = False
 error: str | None = None


class AuditRow(BaseModel):
 audit_id: int
 run_id: str | int
 user_id: int | None = None
 question: str
 sql: str | None = None
 tables_touched: list[str] | None = None
 row_count: int | None = None
 latency_ms: int | None = None
 token_usage: dict | None = None
 created_at: str | None = None
