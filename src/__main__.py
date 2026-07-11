"""Entry point so the app boots via `python -m src` (the canonical run command)."""

import os

import uvicorn

from .main import app


def main() -> None:
    port = int(os.environ.get("PORT", "8001"))
    # host 0.0.0.0 so the parent/launcher can reach it on localhost:8001.
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
