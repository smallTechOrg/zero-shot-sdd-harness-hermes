"""Common helpers — response envelope, error mapping."""

from __future__ import annotations

from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {"data": data, "error": None}


def api_error(code: str, message: str, *, status_code: int = 400):
    from fastapi import HTTPException

    return HTTPException(
        status_code=status_code, detail={"code": code, "message": message}
    )


def error_envelope(code: str, message: str) -> dict[str, Any]:
    """Plain JSON envelope — used by routers that don't wrap in ``ok()``."""
    return {"error": {"code": code, "message": message}}
