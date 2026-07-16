"""FastAPI app factory + lifespan."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cctns_analyst.config.settings import get_settings
from cctns_analyst.db.session import init_db
from cctns_analyst.observability.events import configure_logging, get_logger

log = get_logger("cctns_analyst.api.app_factory")
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "out"


@asynccontextmanager
async def _lifespan(_: FastAPI) -> Any:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info("starting", port=settings.port, mirror_mode="live" if settings.cctns_mirror_url else "mock")
    init_db()
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CCTNS Analyst", version="0.1.0", lifespan=_lifespan)
    from cctns_analyst.api import answer as answer_router
    from cctns_analyst.api import health as health_router

    app.include_router(health_router.router)
    app.include_router(answer_router.router)

    # Mount the Next.js static export at /app/ (single-origin rule).
    if _STATIC_DIR.exists():
        app.mount(
            "/app",
            StaticFiles(directory=str(_STATIC_DIR), html=True, check_dir=False),
            name="frontend",
        )

    @app.get("/")
    def root() -> dict:
        return {
            "service": "cctns_analyst",
            "version": "0.1.0",
            "ui": "/app/",
            "api": "/v1/answer",
            "health": "/health",
        }

    return app


app = create_app()
