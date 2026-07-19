"""`GET /health` — liveness and DB-mode probe."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from mssql_analyst.config.settings import get_settings
from mssql_analyst.observability.events import configure_logging, get_logger

router = APIRouter(tags=["health"])
log = get_logger("mssql_analyst.api.health")


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    configure_logging(settings.log_level)
    # If MSSQL_HOST is set we treat the agent as "wire-ready" — actual
    # connectivity is exercised on the first /api/ask call, where the
    # schema introspection fails fast if the server is unreachable.
    mssql_mode = "live" if (settings.mssql_host or "").strip() else "unconfigured"
    body = {
        "data": {
            "status": "ok",
            "mssql_mode": mssql_mode,
            "version": "0.1.0",
            "llm_model": settings.llm_model,
        },
        "error": None,
    }
    log.info("health", mssql_mode=mssql_mode, llm_model=settings.llm_model)
    return body
