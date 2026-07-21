"""FastAPI app factory + lifespan. Serves the static frontend at /app."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
    app = FastAPI(title="Zero-Shot Agent", version="0.1.0", lifespan=_lifespan)

    from src.api import csv, fraud_detection, health, live_db, runs

    app.include_router(health.router)
    app.include_router(runs.router)
    app.include_router(csv.router, prefix="/csv")
    app.include_router(live_db.router, prefix="/live-db")
    app.include_router(fraud_detection.router, prefix="/fraud-detection")

    if _FRONTEND_DIR.is_dir():
        app.mount("/app", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
