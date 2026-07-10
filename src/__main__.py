"""Entrypoint so `python -m src [--host H] [--port P]` starts the FastAPI server."""
from __future__ import annotations

import argparse
import os

import uvicorn

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Auto-Podcaster backend")
    p.add_argument("--host", default=os.environ.get("AUTO_PODCASTER_HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("AUTO_PODCASTER_PORT", "8001")))
    args = p.parse_args()
    uvicorn.run("src.main:app", host=args.host, port=args.port, reload=False)
