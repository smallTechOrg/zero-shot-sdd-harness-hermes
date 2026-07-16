"""Integration tests — POST /v1/answer via TestClient, with a stub LLM provider.

The stub provider is wired into `cctns_analyst.llm.providers.factory` so it
appears to be the real provider for graph purposes, but its outputs are
scripted. This lets us assert:
- end-to-end behaviour (graph → response → AnswerRun row);
- prompt-spy: the LLM payload sent for each call is captured and asserted
  to contain NO raw row data (data-locality block rule);
- bounded query behaviour against the mock mirror.
"""

from __future__ import annotations

import pytest


# We need to be very careful here. We can't replace the LLMClient module
# function because it's invoked as a class method. Instead, monkeypatch the
# factory to return a RecordingStub.

@pytest.fixture
def recording_provider(monkeypatch):
    """Replace `create_provider` with a stub that records calls and returns
    scripted responses."""
    from cctns_analyst import llm
    from cctns_analyst.llm.providers import base

    calls: list[dict] = []

    class StubProvider(base.LLMProvider):
        def __init__(self) -> None:
            self._responses: list[dict] = [
                # 1st call: nl_to_sql — produce SQL.
                {"sql": "SELECT COUNT(*) AS firs FROM cctns_mirror.fir WHERE district = 'Lucknow'"},
                # 2nd call: summarise — produce prose answer.
                {"answer": "There have been 12 FIRs registered in Lucknow district."},
            ]
            self._idx = 0

        def complete_json(self, *, model: str, system: str, user: str):
            calls.append({"model": model, "system": system, "user": user})
            payload = self._responses[self._idx]
            self._idx += 1
            return payload

    stub = StubProvider()

    def fake(settings):
        return stub

    monkeypatch.setattr(
        "cctns_analyst.llm.providers.factory.create_provider",
        fake,
    )
    # Drop cached client so the factory is re-invoked.
    llm.client.reset_default_llm_client()
    return {"stub": stub, "calls": calls}
