"""Module entry point — `python -m src` and `uv run python -m src`.

Per `harness/patterns/tech-stack.md` the dev port is hard-coded 8001 unless
overridden by the ``PORT`` env var.
"""

from __future__ import annotations

import uvicorn

from cctns_analyst.config.settings import get_settings


def main() -> None:
    s = get_settings()
    # `import_string` requires the importable path uvicorn.evaluate.
    uvicorn.run(
        "cctns_analyst.api:app",
        host="0.0.0.0",
        port=s.port,
        log_level=(s.log_level or "INFO").lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
