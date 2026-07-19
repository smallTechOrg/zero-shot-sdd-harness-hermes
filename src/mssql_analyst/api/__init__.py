"""FastAPI package — app factory, routers.

IMPORTANT: do NOT eagerly build the app at import time (it triggers the
google-genai SDK cold-import on a non-trivial path and slows down even
simple `from mssql_analyst.api import …`). Use the lazy proxies below.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mssql_analyst.api.ask import router as ask_router  # noqa: F401
    from mssql_analyst.api.health import router as health_router  # noqa: F401
    from mssql_analyst.api.usage import router as usage_router  # noqa: F401
    from mssql_analyst.api.app_factory import create_app  # noqa: F401

__all__ = ["ask", "health", "usage", "create_app", "app"]


def __getattr__(name: str):  # PEP 562 — module-level lazy lookup
    import importlib

    if name == "ask":
        return importlib.import_module("mssql_analyst.api.ask")
    if name == "health":
        return importlib.import_module("mssql_analyst.api.health")
    if name == "usage":
        return importlib.import_module("mssql_analyst.api.usage")
    if name == "create_app":
        return importlib.import_module(
            "mssql_analyst.api.app_factory"
        ).create_app
    if name == "app":
        return importlib.import_module(
            "mssql_analyst.api.app_factory"
        ).create_app()
    raise AttributeError(name)
