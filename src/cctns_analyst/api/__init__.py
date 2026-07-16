"""FastAPI package — app factory, routers."""

# IMPORTANT: do NOT eagerly build the app at import time (it triggers the
# google-genai SDK cold-import on a non-trivial path and slows down even
# simple `from cctns_analyst.api import …`). Use the lazy proxies below.

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from cctns_analyst.api.answer import router as answer_router  # noqa: F401
    from cctns_analyst.api.health import router as health_router  # noqa: F401
    from cctns_analyst.api.app_factory import create_app  # noqa: F401

__all__ = ["answer", "health", "create_app", "app"]


def __getattr__(name: str):  # PEP 562 — module-level lazy lookup
    # Avoid recursive `from cctns_analyst.api import X as m` (would re-enter __getattr__).
    import importlib

    if name == "answer":
        return importlib.import_module("cctns_analyst.api.answer")
    if name == "health":
        return importlib.import_module("cctns_analyst.api.health")
    if name == "create_app":
        return importlib.import_module(
            "cctns_analyst.api.app_factory"
        ).create_app
    if name == "app":
        return importlib.import_module(
            "cctns_analyst.api.app_factory"
        ).create_app()
    raise AttributeError(name)
