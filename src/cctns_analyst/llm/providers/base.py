"""Provider base — abstract LLMProvider so other providers can be added."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface every LLM provider implements."""

    @abstractmethod
    def complete_json(
        self, *, model: str, system: str, user: str
    ) -> Any:
        """Run a single chat completion. Must return either ``dict`` or ``str``.

        ``dict`` ⇒ parsed JSON. ``str`` ⇒ free text the caller can parse.
        """
        raise NotImplementedError
