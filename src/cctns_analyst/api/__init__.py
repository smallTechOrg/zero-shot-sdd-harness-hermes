"""FastAPI package — app factory, routers."""

# IMPORTANT: do NOT eagerly build the app at import time (it triggers the
# google-genai SDK cold-import on a non-trivial path and slows down even
# simple `from cctns_analyst.api import …`). Use the lazy proxies below.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cctns_analyst.api.answer import router as answer_router
    from cctns_analyst.api.health import router as health_router
    from cctns_analyst.api.app_factory import create_app


def __getattr__(name: str):  # PEP 562 — module-level lazy lookup
    if name in {"answer", "answer_router"}:
        from cctns_analyst.api import answer as m
        return m
    if name in {"health", "health_router"}:
        from cctns_analyst.api import health as m
        return m
    if name == "create_app":
        from cctns_analyst.api.app_factory import create_app as fn
        return fn
    if name == "app":
        from cctns_analyst.api.app_factory import create_app as fn
        return fn()
    raise AttributeError(name)
