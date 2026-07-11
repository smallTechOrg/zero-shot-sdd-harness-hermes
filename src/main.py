"""FastAPI backend for the AI Music Tutor (Phase 1: note naming).

Serves the REST + SSE API AND the built Next.js UI at /app.
Note-name correctness is always COMPUTED (src.music.theory) — never from the LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .db import ensure_student, get_mastery, init_db
from .drill import check_answer, make_exercise, suggest_next_topic, topic_for
from .llm import generate_teaching
from .schemas import (
    CheckRequest,
    CheckResponse,
    ExerciseOut,
    NextRequest,
    StartRequest,
    StartResponse,
    TeachingOut,
)
from .synth import synth_wav_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("music_tutor")

# In-memory drill sessions: drill_id -> {student_id, clefs, current exercise}
_SESSIONS: dict[str, dict] = {}

_FRONTEND_OUT = Path(__file__).resolve().parent.parent / "frontend" / "out"


def _envelope(data, error=None):
    return {"data": data, "error": error}


def ok(data):
    return _envelope(data)


def api_error(code: str, message: str, status: int = 400):
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def get_exercise(drill_id: str) -> dict:
    sess = _SESSIONS.get(drill_id)
    if not sess:
        raise HTTPException(status_code=404, detail="unknown drill_id")
    ex = sess.get("current")
    if not ex:
        raise HTTPException(status_code=404, detail="no current exercise")
    return ex


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AI Music Tutor", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        return ok({"status": "ok", "version": __version__})

    @app.post("/api/exercises/start", response_model=None)
    async def start(req: StartRequest):
        t0 = time.time()
        if not req.clefs or any(c not in ("treble", "bass") for c in req.clefs):
            return api_error("bad_clefs", "clefs must be subset of ['treble','bass']")
        ensure_student(req.student_id, req.display_name)
        # ONE Gemini call per drill set (teaching text only).
        teaching = generate_teaching(
            topic="reading notes on the staff", clef=req.clefs[0]
        )
        drill_id = f"drill_{os.urandom(6).hex()}"
        ex = make_exercise(req.student_id, req.clefs)
        ex["drill_id"] = drill_id
        _SESSIONS[drill_id] = {
            "student_id": req.student_id,
            "clefs": req.clefs,
            "current": ex,
            "teaching": teaching,
        }
        logger.info(
            "start drill=%s student=%s clefs=%s llm_fallback=%s dt=%.2fs",
            drill_id, req.student_id, req.clefs, teaching["used_fallback"],
            time.time() - t0,
        )
        return ok(StartResponse(
            drill_id=drill_id,
            teaching=TeachingOut(**teaching),
            exercise=ExerciseOut(**ex),
        ).model_dump())

    @app.post("/api/notes/next", response_model=None)
    async def next_note(req: NextRequest):
        sess = _SESSIONS.get(req.drill_id)
        if not sess:
            return api_error("bad_drill", "unknown drill_id", 404)
        ex = make_exercise(sess["student_id"], sess["clefs"])
        ex["drill_id"] = req.drill_id
        sess["current"] = ex
        return ok(ExerciseOut(**ex).model_dump())

    @app.get("/api/notes/stream")
    async def stream_notes(drill_id: str = Query(...), student_id: str = Query(...)):
        sess = _SESSIONS.get(drill_id)
        if not sess or sess["student_id"] != student_id:
            return api_error("bad_drill", "unknown drill_id", 404)

        async def event_gen():
            # Stream a few upcoming notes so the UI can pre-load audio.
            for _ in range(3):
                ex = make_exercise(student_id, sess["clefs"])
                ex["drill_id"] = drill_id
                yield f"data: {json.dumps(ExerciseOut(**ex).model_dump())}\n\n"
                await asyncio.sleep(0.05)

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.post("/api/notes/{note_id}/check", response_model=None)
    async def check(note_id: str, req: CheckRequest):
        # locate the exercise by id across sessions
        ex = None
        student_id = None
        for sess in _SESSIONS.values():
            cur = sess.get("current")
            if cur and cur["id"] == note_id:
                ex = cur
                student_id = sess["student_id"]
                break
        if not ex or not student_id:
            return api_error("bad_note", "unknown note_id", 404)
        result = check_answer(ex, req.student_answer, student_id)
        return ok(CheckResponse(**result).model_dump())

    @app.get("/api/notes/{note_id}/audio")
    async def audio(note_id: str):
        ex = get_exercise_by_id(note_id)
        if not ex:
            return api_error("bad_note", "unknown note_id", 404)
        wav = synth_wav_bytes(ex["midi"])
        return Response(content=wav, media_type="audio/wav")

    @app.get("/api/notes/{note_id}/speak")
    async def speak(note_id: str, text: str = Query(...)):
        from .speech import speak_mp3

        try:
            mp3 = await speak_mp3(text)
        except Exception as exc:
            logger.warning("edge-tts failed: %s", exc)
            return api_error("tts_unavailable", "speech unavailable", 503)
        return Response(content=mp3, media_type="audio/mpeg")

    @app.get("/api/mastery", response_model=None)
    async def mastery(student_id: str = Query(...)):
        return ok(get_mastery(student_id))

    @app.get("/api/suggest", response_model=None)
    async def suggest(student_id: str = Query(...), clefs: str = Query("treble")):
        topic = suggest_next_topic(student_id, clefs.split(","))
        return ok({"topic": topic})

    return app


def get_exercise_by_id(note_id: str) -> dict | None:
    for sess in _SESSIONS.values():
        cur = sess.get("current")
        if cur and cur["id"] == note_id:
            return cur
    return None


app = create_app()

# Serve the built Next.js UI at /app (single-origin path).
if _FRONTEND_OUT.exists():
    app.mount("/app", StaticFiles(directory=str(_FRONTEND_OUT), html=True), name="ui")
else:
    @app.get("/app/")
    async def app_missing():
        return JSONResponse(
            status_code=200,
            content={
                "message": "UI not built. Run: cd frontend && npm install && npm run build"
            },
        )

