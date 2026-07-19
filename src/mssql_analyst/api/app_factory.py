"""FastAPI app factory + lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mssql_analyst.config.settings import get_settings
from mssql_analyst.db.session import init_db
from mssql_analyst.observability.events import configure_logging, get_logger

log = get_logger("mssql_analyst.api.app_factory")
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "out"


@asynccontextmanager
async def _lifespan(_: FastAPI) -> Any:
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info(
        "starting",
        port=settings.port,
        mssql_host=settings.mssql_host or "(unset)",
        mssql_db=settings.mssql_db,
        llm_model=settings.llm_model,
    )
    init_db()
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MSSQL Analyst", version="0.1.0", lifespan=_lifespan)

    from mssql_analyst.api import ask as ask_router  # lazy
    from mssql_analyst.api import health as health_router  # lazy
    from mssql_analyst.api import phase2 as phase2_router  # lazy
    from mssql_analyst.api import phase3 as phase3_router  # lazy
    from mssql_analyst.api import usage as usage_router  # lazy

    app.include_router(health_router.router)
    app.include_router(ask_router.router)
    app.include_router(phase2_router.router)
    app.include_router(phase3_router.router)
    app.include_router(usage_router.router)

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
            "service": "mssql_analyst",
            "version": "0.1.0",
            "ui": "/app/",
            "api": "/api/ask",
            "health": "/health",
        }

    return app


app = create_app()
