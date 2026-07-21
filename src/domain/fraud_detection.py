"""Domain models — fraud detection analyst shapes."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FraudDetectionQueryRequest(BaseModel):
 question: str = Field(..., min_length=1, max_length=5_000)
 schema_summary: str | None = Field(default=None, max_length=20_000)
 row_limit: int | None = Field(default=None, ge=1, le=500_000)


class FraudDetectionQueryResponse(BaseModel):
 run_id: str
 status: str
 data_source: str = "fraud_detection"
 generated_sql: str | None = None
 tables_touched: list[str] | None = None
 executed_row_count: int | None = None
 latency_ms: int | None = None
 provider: str | None = None
 model: str | None = None
 error: str | None = None
 answer_text: str | None = None
 result_table: dict | None = None
 served_from_cache: bool = False
 anomaly_flags: list[str] | None = None
 sensitive_warning: str | None = None
