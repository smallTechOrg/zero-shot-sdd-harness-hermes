"""Phase-3 retry-path integration test.

Wires a stub LLM that returns:
  attempt 1: ``SELECT * FROM INFORMATION_SCHEMA.TABLES`` (validator rejects)
  attempt 2: ``SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES``
              (accepted, bounded)

After the run, the audit row should show ``sql_attempts==2`` and the
timeline should include BOTH attempts: nl_to_sql twice, validate_sql
twice, then execute_sql once.
"""

from __future__ import annotations

from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

# Shared counters outside the instance — pytest's fixture patching
# produces a NEW instance each time the runner calls
# ``get_mssql_connector()``, so we must tally via module-level counters
# rather than via the captured instance's attribute.
SHARED_COUNTERS = {
    "describe_calls": 0,
    "execute_calls": 0,
    "executed_sqls": [],
}


class _FakeConnector:
    """Stub connector used by the integration test.

    Counts are written into ``SHARED_COUNTERS`` so the test can verify
    regardless of how many instances the runner's lazy-imported
    ``get_mssql_connector()`` produces.
    """

    def __init__(self) -> None:
        pass

    def describe_schema(self):
        SHARED_COUNTERS["describe_calls"] += 1
        return {
            "INFORMATION_SCHEMA.TABLES": [
                {"name": "TABLE_NAME", "type": "varchar"},
                {"name": "TABLE_TYPE", "type": "varchar"},
            ],
        }

    def execute(self, sql: str):
        SHARED_COUNTERS["execute_calls"] += 1
        SHARED_COUNTERS["executed_sqls"].append(sql)
        return ["n"], [(74,)], 1


class _StubLLM:
    """Stub LLM provider that returns one response then another.

    Each script entry is wrapped in a fresh ``LLMCallResult`` with
    token counts so the runner sees proper ``total_tokens`` aggregate.
    """

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._idx = 0
        # Each entry is a (content_dict, input_tokens, output_tokens) tuple.
        self._responses: list[tuple[dict[str, str], int, int]] = [
            # attempt 1 — bad SQL (unbounded SELECT *, no WHERE, no TOP)
            (
                {"sql": "SELECT * FROM INFORMATION_SCHEMA.TABLES"},
                100,
                20,
            ),
            # attempt 2 — clean bounded SQL
            (
                {"sql": "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES"},
                100,
                20,
            ),
        ]

    def complete_json(self, *, model, system, user):
        self.calls.append({"model": model, "system": system, "user": user})
        from mssql_analyst.llm.types import LLMCallResult

        if self._idx >= len(self._responses):
            raise RuntimeError(
                f"no more scripted responses at _idx={self._idx}, len={len(self._responses)}"
            )
        payload, in_tok, out_tok = self._responses[self._idx]
        self._idx += 1
        return LLMCallResult(payload, input_tokens=in_tok, output_tokens=out_tok)


@pytest.fixture
def retry_environment(monkeypatch):
    """Wire the stub LLM + FakeConnector class into the production runner.

    The runner does a lazy ``from … import get_default_llm_client`` inside
    ``run_agent``, then calls it. The cleanest way to swap is to patch
    ``llm.client.get_default_llm_client`` AND clear the cached client.
    Then ``from … import get_default_llm_client`` resolves to the patched
    name at call-time. (The import statement binds the local name
    eagerly on each call, so the patch is always visible.)
    """
    import mssql_analyst.llm.client as llm_client_mod
    import mssql_analyst.tools.mssql as mssql_mod
    from mssql_analyst.llm.client import LLMClient

    fake_llm = _StubLLM()
    wrapper = LLMClient(fake_llm, model="test-model")

    def fake_get_default_llm_client() -> LLMClient:
        return wrapper

    # Patch the source module's symbol; the runner's local rebinding on
    # each ``from … import get_default_llm_client`` picks this up.
    monkeypatch.setattr(
        llm_client_mod, "get_default_llm_client", fake_get_default_llm_client
    )
    llm_client_mod.reset_default_llm_client()
    if hasattr(llm_client_mod, "_default_client"):
        llm_client_mod._default_client = None

    FakeConnectorType = type(_FakeConnector())
    monkeypatch.setattr(mssql_mod, "MssqlConnector", FakeConnectorType)
    mssql_mod.reset_mssql_connector()
    return {"llm": fake_llm}

def test_phase3_validator_retry_reaches_execute_on_attempt_two(
    temp_sqlite_db, retry_environment
):
    """End-to-end: validator-reject on attempt 1 cycles back; attempt 2 accepts."""
    from mssql_analyst.graph.runner import run_agent

    # Reset shared counters to keep the assertion clean.
    SHARED_COUNTERS["describe_calls"] = 0
    SHARED_COUNTERS["execute_calls"] = 0
    SHARED_COUNTERS["executed_sqls"] = []

    final = run_agent("How many tables are in master?", request_id="phase3-retry-test")
    assert final["status"] == "completed", final

    # Two LLM calls; one executor call.
    assert len(retry_environment["llm"].calls) == 2
    assert SHARED_COUNTERS["execute_calls"] == 1
    assert "COUNT(*)" in SHARED_COUNTERS["executed_sqls"][0]

    # sql_attempts == 2.
    assert final["sql_attempts"] == 2

    timeline_nodes = [e["node"] for e in final["timelines"]]
    assert timeline_nodes.count("nl_to_sql") == 2
    assert timeline_nodes.count("validate_sql") == 2
    assert timeline_nodes.count("execute_sql") == 1

    validate_entries = [e for e in final["timelines"] if e["node"] == "validate_sql"]
    assert validate_entries[0].get("clean") is False
    assert validate_entries[0].get("complaints", 0) >= 1
    assert validate_entries[1].get("clean") is True

    execute_entry = next(
        e for e in final["timelines"] if e["node"] == "execute_sql"
    )
    # tokens=200+40=240 → tokens_used sum. Below 30k high-water mark →
    # row_cap_effective stays at base cap (1000).
    assert final["tokens_used"] == 240
    assert execute_entry["row_cap_effective"] == 1000


def test_phase3_token_aware_shrink(temp_sqlite_db, retry_environment):
    """tokens_used > 30k shrinks row-cap during execute_sql."""
    from mssql_analyst.llm.types import LLMCallResult
    from mssql_analyst.graph.runner import run_agent

    SHARED_COUNTERS["describe_calls"] = 0
    SHARED_COUNTERS["execute_calls"] = 0
    SHARED_COUNTERS["executed_sqls"] = []
    retry_environment["llm"]._responses = [
        (
            {"sql": "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.TABLES"},
            80_000,
            2_000,
        ),
    ]
    final = run_agent("count tables", request_id="phase3-token-aware-test")
    assert final["status"] == "completed", final
    assert final["tokens_used"] == 82_000
    assert final["row_cap_effective"] == 500
    assert SHARED_COUNTERS["execute_calls"] == 1

    execute_entry = next(
        e for e in final["timelines"] if e["node"] == "execute_sql"
    )
    assert execute_entry["row_cap_effective"] == 500
