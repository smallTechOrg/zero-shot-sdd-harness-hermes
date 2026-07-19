"""Provider base — abstract ``LLMProvider`` so other providers can be added."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union

from mssql_analyst.llm.types import LLMCallResult


class LLMProvider(ABC):
    """Abstract interface every LLM provider implements."""

    @abstractmethod
    def complete_json(
        self, *, model: str, system: str, user: str
    ) -> Union[LLMCallResult, dict, str, Any]:
        """Run a single chat completion.

        Prefer returning ``LLMCallResult``. Bare ``dict`` / ``str`` is also
        accepted by the client (legacy compatibility) — callers treat both
        shapes via ``LLMCallResult``.
        """
        raise NotImplementedError
