"""Domain types — small Pydantic models for shape-only data crossing boundaries."""

from mssql_analyst.domain.ask import AskRequest, AskResponse
from mssql_analyst.domain.phase2 import (
    AskRunIdError,
    HistoryResponse,
    HistoryRow,
    UsageByDayResponse,
    UsageDayBucket,
)
from mssql_analyst.domain.usage import UsageResponse

__all__ = [
    "AskRequest",
    "AskResponse",
    "AskRunIdError",
    "HistoryResponse",
    "HistoryRow",
    "UsageByDayResponse",
    "UsageDayBucket",
    "UsageResponse",
]
