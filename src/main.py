"""FastAPI app for Auto-Podcaster.

Endpoints:
  GET  /health                                  -> liveness
  POST /api/podcast/generate                    -> start a generation, returns session_id
  GET  /api/podcast/stream/{session_id}         -> SSE audio stream
  GET  /api/podcast/download/{session_id}       -> download the finished mp3

No agent framework: the pipeline is a deterministic dialogue->TTS->stream flow.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .config import config
from .db import create_session, get_session, init_db
from .graph.stream import run_pipeline
from .prompts import CAST
from .schemas import GenerateRequest, GenerateResponse

app = FastAPI(title="Auto-Podcaster", version="0.1.0")

# Local single-user: allow the Next.js dev origin. Tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "gemini_key_present": config.gemini_key_present}


@app.get("/api/podcast/cast")
def list_cast() -> dict:
    """Expose the fixed cast (ids, names, personas) for the frontend picker."""
    return {
        "cast": [
            {"id": h.id, "name": h.name, "persona": h.persona, "voice": h.voice}
            for h in CAST.values()
        ]
    }


@app.post("/api/podcast/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    # Validate host ids against the fixed cast.
    unknown = [h for h in req.hosts if h not in CAST]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown host id(s): {unknown}")

    session_id = uuid.uuid4().hex
    audio_path = str(config.DATA_DIR / f"{session_id}.mp3")
    create_session(session_id, req.topic, req.hosts, audio_path)
    return GenerateResponse(session_id=session_id, status="generating")


@app.get("/api/podcast/stream/{session_id}")
def stream(session_id: str):
    sess = get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    if sess["status"] == "done":
        # Already finished — replay is not supported; client should download.
        raise HTTPException(status_code=409, detail="Session already finished; use download.")
    if sess["status"] == "failed":
        raise HTTPException(status_code=410, detail=f"Session failed: {sess['error']}")

    audio_path = sess["audio_path"]

    async def event_gen():
        async for sse in run_pipeline(session_id, sess["topic"], _hosts(sess), audio_path):
            yield sse

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/podcast/download/{session_id}")
def download(session_id: str):
    sess = get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    if sess["status"] != "done" or not sess["audio_path"]:
        raise HTTPException(status_code=404, detail="Audio not ready")
    path = Path(sess["audio_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{session_id}.mp3")


def _hosts(sess: dict) -> list[str]:
    import json
    return json.loads(sess["hosts"])
