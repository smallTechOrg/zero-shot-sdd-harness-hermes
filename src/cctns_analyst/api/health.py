"""`GET /health` returns ok + mirror mode."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from cctns_analyst.api._common import ok
from cctns_analyst.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(s: Settings = Depends(get_settings)) -> dict:
    mode = "live" if (s.cctns_mirror_url or "").strip() else "mock"
    return ok(
        {
            "status": "ok",
            "mirror_mode": mode,
            "version": "0.1.0",
        }
    )
