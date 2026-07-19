"""Wire-protocol types shared by LLM providers and the client.

Defined in its own module so providers (which import base) and the client
(which imports providers) don't form a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMCallResult:
    """Captured result of one LLM call — parsed payload + reported token usage."""

    content: Any = None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return int(self.input_tokens or 0) + int(self.output_tokens or 0)
