from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from analytics_agent.api._common import api_error, ok
from analytics_agent.api.health import router as health_router
from analytics_agent.api.routes import router as routes_router
from analytics_agent.observability.events import configure_logging, get_logger

logger = get_logger("app")

FRONTEND_DIR = "frontend/out"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    configure_logging()
    from analytics_agent.db.session import init_db

    init_db()
    logger.info("app.startup", frontend=FRONTEND_DIR)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Full Stack Analytics Agent", version="0.1.0", lifespan=_lifespan)
    app.include_router(health_router)
    app.include_router(routes_router)

    import os

    if os.path.isdir(FRONTEND_DIR):
        app.mount("/app/_static", StaticFiles(directory=FRONTEND_DIR), name="frontend_static")

        @app.get("/app/{full_path:path}")
        async def _serve_spa(full_path: str = ""):
            import os

            file_path = os.path.join(FRONTEND_DIR, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            index = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.isfile(index):
                return FileResponse(index)
            return api_error("frontend_missing", "frontend not built — run `cd frontend && npm run build`", 404)

    return app


app = create_app()
