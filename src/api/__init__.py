"""FastAPI app factory + lifespan. Serves the static frontend at /app."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "public"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from src.config.settings import get_settings
    from src.db.session import init_db
    from src.observability.events import configure_logging

    configure_logging(get_settings().log_level)
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="UP Police Data Analyst", version="0.1.0", lifespan=_lifespan)

    from src.api import health, routes_ingest as v1_ingest
    from src.api import routes_query as v1_query
    from src.api import routes_db
    from src.api import runs

    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(v1_ingest.router, prefix="/api/v1", tags=["ingest"])
    app.include_router(v1_query.router, prefix="/api/v1", tags=["query"])
    app.include_router(routes_db.router, prefix="/api/v1", tags=["db"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if _FRONTEND_DIR.is_dir():
        app.mount("/app", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
