"""Domain types — small Pydantic models for shape-only data crossing boundaries."""

from mssql_analyst.domain.ask import AskRequest, AskResponse
from mssql_analyst.domain.usage import UsageResponse

__all__ = ["AskRequest", "AskResponse", "UsageResponse"]
