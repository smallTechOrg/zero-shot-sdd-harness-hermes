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
from .curriculum import topic_blocks
from .db import (
    ensure_student,
    get_all_sched,
    get_mastery,
    init_db,
)
from .drill import (
    check_answer,
    check_melody,
    check_phrase,
    check_rhythm_dictation,
    make_exercise,
    suggest_next_topic,
    topic_for,
)
from .llm import generate_teaching
from .schemas import (
    CheckRequest,
    CheckResponse,
    CurriculumTopic,
    DictationCheckRequest,
    ExerciseOut,
    NextRequest,
    PhraseCheckRequest,
    StartRequest,
    StartResponse,
    SuggestOut,
    TeachingOut,
)
from .synth import (
    DEFAULT_BPM,
    synth_melody_wav_bytes,
    synth_phrase_wav_bytes,
    synth_rhythm_wav_bytes,
    synth_wav_bytes,
)

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
        if req.drill_type not in ("note", "rhythm", "phrase", "melody", "rhythm-dictation"):
            return api_error("bad_drill_type", "drill_type must be 'note', 'rhythm', 'phrase', 'melody', or 'rhythm-dictation'")
        ensure_student(req.student_id, req.display_name)
        # ONE Gemini call per drill set (teaching text only).
        teaching = generate_teaching(
            topic="reading notes on the staff", clef=req.clefs[0]
        )
        drill_id = f"drill_{os.urandom(6).hex()}"
        ex = make_exercise(req.student_id, req.clefs, drill_type=req.drill_type)
        ex["drill_id"] = drill_id
        _SESSIONS[drill_id] = {
            "student_id": req.student_id,
            "clefs": req.clefs,
            "drill_type": req.drill_type,
            "current": ex,
            "teaching": teaching,
        }
        logger.info(
            "start drill=%s student=%s clefs=%s type=%s llm_fallback=%s dt=%.2fs",
            drill_id, req.student_id, req.clefs, req.drill_type,
            teaching["used_fallback"], time.time() - t0,
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
        drill_type = req.drill_type or sess.get("drill_type", "note")
        sess["drill_type"] = drill_type
        ex = make_exercise(sess["student_id"], sess["clefs"], drill_type=drill_type)
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
                ex = make_exercise(
                    student_id, sess["clefs"], drill_type=sess.get("drill_type", "note")
                )
                ex["drill_id"] = drill_id
                yield f"data: {json.dumps(ExerciseOut(**ex).model_dump())}\n\n"
                await asyncio.sleep(0.05)

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.get("/api/curriculum", response_model=None)
    async def curriculum(clefs: str = Query("treble,bass")):
        """The full set of drillable topics (note per clef + rhythm)."""
        blocks = topic_blocks(clefs.split(","))
        return ok([CurriculumTopic(**b).model_dump() for b in blocks.values()])

    @app.get("/api/dashboard", response_model=None)
    async def dashboard(student_id: str = Query(...), clefs: str = Query("treble,bass")):
        """Per-topic mastery + scheduling + the next-topic suggestion.

        Returns topics with per-item progress bars (weight, box, attempts)
        and a proactive `suggest` block for the UI to surface."""
        mastery = {m["topic"]: m for m in get_mastery(student_id)}
        sched = {s["item_id"]: s for s in get_all_sched(student_id)}
        blocks = topic_blocks(clefs.split(","))
        topics = []
        for tid, blk in blocks.items():
            items = []
            for iid in blk["items"]:
                m = mastery.get(iid, {"weight": 0.3, "attempts": 0, "correct": 0})
                s = sched.get(iid, {"box": 0, "streak": 0, "lapses": 0})
                items.append({
                    "item_id": iid,
                    "weight": m["weight"],
                    "attempts": m["attempts"],
                    "correct": m["correct"],
                    "box": s["box"],
                    "streak": s["streak"],
                    "lapses": s["lapses"],
                })
            topics.append({
                "id": tid,
                "label": blk["label"],
                "type": blk["type"],
                "items": items,
            })
        suggest = suggest_next_topic(student_id, clefs.split(","))
        return ok({"topics": topics, "suggest": suggest})

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
        # Rhythm exercises have no pitch — no audio (UI hides the play button).
        if ex.get("type") == "rhythm" or ex.get("midi") is None:
            return api_error("no_audio", "rhythm symbol has no pitch audio", 404)
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

    # ----------------------------------------------------------------------- #
    # Phase 3 — Sight-reading & transcription (metronome-backed playback)
    # ----------------------------------------------------------------------- #
    @app.get("/api/phrase/{phrase_id}/audio", response_model=None)
    async def phrase_audio(
        phrase_id: str,
        bpm: float = Query(DEFAULT_BPM),
        lead_in: int = Query(2),
    ):
        ex = get_exercise_by_id(phrase_id)
        if not ex:
            return api_error("bad_phrase", "unknown phrase_id", 404)
        if ex.get("type") != "phrase" or not ex.get("phrase"):
            return api_error("bad_phrase", "exercise is not a phrase", 400)
        from .music import phrase as P

        phrase = {"clef": ex["clef"], "steps": ex["phrase"]}
        # Phase 4: also give the sight-reading playback a metronome pulse.
        wav = synth_phrase_wav_bytes(phrase, bpm=bpm, lead_in=lead_in)
        return Response(content=wav, media_type="audio/wav")

    @app.post("/api/phrase/{phrase_id}/check", response_model=None)
    async def phrase_check(phrase_id: str, req: PhraseCheckRequest):
        ex = None
        student_id = None
        for sess in _SESSIONS.values():
            cur = sess.get("current")
            if cur and cur["id"] == phrase_id:
                ex = cur
                student_id = sess["student_id"]
                break
        if not ex or not student_id:
            return api_error("bad_phrase", "unknown phrase_id", 404)
        if ex.get("type") != "phrase":
            return api_error("bad_phrase", "exercise is not a phrase", 400)
        result = check_phrase(ex, req.submitted, student_id)
        return ok(result)

    # ----------------------------------------------------------------------- #
    # Phase 4 — Writing notation (dictation): melody + rhythm
    # ----------------------------------------------------------------------- #
    @app.get("/api/dictation/{dict_id}/audio", response_model=None)
    async def dictation_audio(
        dict_id: str,
        bpm: float = Query(DEFAULT_BPM),
        lead_in: int = Query(4),
    ):
        ex = get_exercise_by_id(dict_id)
        if not ex:
            return api_error("bad_dictation", "unknown dictation_id", 404)
        dtype = ex.get("type")
        if dtype == "melody" and ex.get("phrase"):
            melody = {"clef": ex["clef"], "steps": ex["phrase"]}
            wav = synth_melody_wav_bytes(melody, bpm=bpm, lead_in=lead_in)
        elif dtype == "rhythm-dictation":
            pattern = {"steps": ex.get("steps_meta") or []}
            wav = synth_rhythm_wav_bytes(pattern, bpm=bpm, lead_in=lead_in)
        else:
            return api_error("bad_dictation", "exercise is not dictation", 400)
        return Response(content=wav, media_type="audio/wav")

    @app.post("/api/dictation/{dict_id}/check", response_model=None)
    async def dictation_check(dict_id: str, req: DictationCheckRequest):
        ex = None
        student_id = None
        for sess in _SESSIONS.values():
            cur = sess.get("current")
            if cur and cur["id"] == dict_id:
                ex = cur
                student_id = sess["student_id"]
                break
        if not ex or not student_id:
            return api_error("bad_dictation", "unknown dictation_id", 404)
        dtype = ex.get("type")
        if dtype == "melody":
            result = check_melody(ex, req.submitted, student_id)
        elif dtype == "rhythm-dictation":
            result = check_rhythm_dictation(ex, req.submitted, student_id)
        else:
            return api_error("bad_dictation", "exercise is not dictation", 400)
        return ok(result)

    @app.get("/api/mastery", response_model=None)
    async def mastery(student_id: str = Query(...)):
        return ok(get_mastery(student_id))

    @app.get("/api/suggest", response_model=None)
    async def suggest(
        student_id: str = Query(...),
        clefs: str = Query("treble"),
        drill_type: str = Query("note"),
    ):
        s = suggest_next_topic(student_id, clefs.split(","))
        # Honour an explicit drill_type override (e.g. rhythm drill selected).
        if drill_type == "rhythm" and s.get("type") != "rhythm":
            s = {**s, "topic_id": "rhythm", "label": "Rhythm / duration naming",
                 "type": "rhythm", "drill_type": "rhythm",
                 "reason": "Rhythm drill selected — practise naming durations."}
        return ok(s)

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

