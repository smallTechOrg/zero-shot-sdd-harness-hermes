"""Module entry point — `python -m src` and `.venv/bin/python -m src`.

Per `harness/patterns/tech-stack.md` the dev port is hard-coded 8001
unless overridden by the AGENT_PORT env var (Pydantic-settings reads it).
"""

from __future__ import annotations

import uvicorn


def main() -> None:
    from mssql_analyst.config.settings import get_settings

    s = get_settings()
    uvicorn.run(
        "mssql_analyst.api:app",
        host="0.0.0.0",
        port=s.port,
        log_level=(s.log_level or "INFO").lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
