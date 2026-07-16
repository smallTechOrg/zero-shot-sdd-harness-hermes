"""Structured JSON logging configured for the CCTNS analyst.

Every line is JSON with fields:
- timestamp, level, request_id, run_id, message
- plus request-scoped extras (question, sql_template, latency_ms, row_count,
  token_count, error, ...)

`structlog` is the renderer. We emit to stdout (and optionally a file). We
never include API keys / token values — only their presence boolean.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)

_configured = False


def configure_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=lvl,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(lvl),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str = "cctns_analyst") -> Any:
    configure_logging()
    return structlog.get_logger(name)


def new_request_id() -> str:
    rid = str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def bind_request_context(*, request_id: str | None = None, run_id: str | None = None) -> None:
    if request_id is not None:
        _request_id_var.set(request_id)
    if run_id is not None:
        _run_id_var.set(run_id)


def unbind_request_context() -> None:
    _request_id_var.set(None)
    _run_id_var.set(None)


def _add_context(_: Any, __: str, event_dict: dict) -> dict:
    rid = _request_id_var.get()
    if rid:
        event_dict.setdefault("request_id", rid)
    run = _run_id_var.get()
    if run:
        event_dict.setdefault("run_id", run)
    return event_dict
