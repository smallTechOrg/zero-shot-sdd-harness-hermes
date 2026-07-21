"""Graph nodes — Phase 1 capability: analyze_data; Phase 2 adds optional MsSQL cache routing."""
from __future__ import annotations

from src.db.mssql import cache_get, cache_set, has_mssql, live_query
from src.graph.state import AgentState
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError


def _likely_sql_topic(instruction: str) -> bool:
    q = instruction.lower()
    return any(k in q for k in ["total", "count", "sum", "average", "avg", "max", "min", "district", "station", "fir", "crime", "accused", "victim", "case"])


def analyze_data(state: AgentState) -> AgentState:
    try:
        use_mssql = bool(state.get("use_mssql")) and has_mssql()
        probe_sql = (
            "SELECT TOP 10 * FROM sys.tables"
            if use_mssql and _likely_sql_topic(state.get("instruction", ""))
            else None
        )
        cache_hit = False
        query_hash = None

        if use_mssql and probe_sql:
            query_hash = (
                __import__("hashlib").sha256(probe_sql.encode("utf-8")).hexdigest()[:16]
            )
            cached = cache_get(probe_sql)
            if cached is not None:
                cache_hit = True
                return {
                    "output_text": cached["output_text"],
                    "provider": cached.get("provider", ""),
                    "model": cached.get("model", ""),
                    "file_count": int(state.get("file_count") or 0),
                    "cache_hit": cache_hit,
                    "query_hash": query_hash,
                    "error": None,
                }

        client = LLMClient()
        system = load_prompt("analyze")
        content = state["input_text"]
        if probe_sql:
            try:
                live_rows = live_query(probe_sql)
                content += "\n\nPHASE2_LIVE_MSSQL_SAMPLE:\n" + json.dumps(live_rows[:25], default=str)
            except Exception as exc:
                content += f"\n\nPHASE2_LIVE_MSSQL_ERROR: {exc}\n"

        output = client.complete(system, content, max_tokens=2048)
        payload = {"output_text": output, "provider": client.provider_name, "model": client.model}

        if use_mssql and probe_sql:
            try:
                cache_set(probe_sql, payload)
            except Exception:
                pass

        return {
            "output_text": output,
            "provider": client.provider_name,
            "model": client.model,
            "file_count": int(state.get("file_count") or 0),
            "cache_hit": cache_hit,
            "query_hash": query_hash,
            "error": None,
        }
    except LLMError as exc:
        return {"error": str(exc)}


def handle_error(state: AgentState) -> AgentState:
    return {"status": "failed"}


def finalize(state: AgentState) -> AgentState:
    return {"status": "completed"}
