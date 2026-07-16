"""Domain types — small Pydantic models for shape-only data crossing boundaries."""

from cctns_analyst.domain.question import AnswerRequest
from cctns_analyst.domain.answer_run import AnswerRunSummary

__all__ = ["AnswerRequest", "AnswerRunSummary"]
