"""Stream orchestration: dialogue -> TTS -> SSE, while persisting the mp3 file.

This module builds the async generator that the FastAPI endpoint streams to the
client. Each TTS chunk is (a) yielded as an SSE `audio` event and (b) appended to
the session's output file. On completion it finalizes the file and marks the
session `done`; on failure it marks `failed` and emits an `error` event.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from ..config import config
from ..db import update_status
from .tts import synthesize_turn
from .dialogue import stream_turns, DialogueError, Turn
from .transcode import mp3_chunk_to_webm, WEBM_MIME


def _sse(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


async def run_pipeline(session_id: str, topic: str, host_ids: list[str], audio_path: str):
    """Drive one podcast generation, yielding SSE-formatted strings.

    Writes audio chunks to `audio_path` as they arrive so the file is the
    authoritative download artifact.
    """
    path = Path(audio_path)
    total_bytes = 0
    turn_count = 0
    try:
        with path.open("wb") as f:
            async for turn in stream_turns(topic, host_ids):
                turn_count += 1
                # Collect the FULL line's mp3 first (edge-tts fragments aren't
                # individually valid mp3; a whole turn is). Then transcode once
                # to a standalone webm segment we can append live via MSE.
                mp3_buf = b""
                async for chunk in synthesize_turn(turn.text, turn.speaker):
                    mp3_buf += chunk
                    f.write(chunk)
                    total_bytes += len(chunk)
                webm = mp3_chunk_to_webm(mp3_buf)
                yield _sse("audio", base64.b64encode(webm).decode("ascii"))

        if turn_count == 0:
            raise DialogueError("Gemini produced no usable dialogue turns.")

        update_status(session_id, "done", audio_path=str(path))
        yield _sse(
            "done",
            json.dumps(
                {
                    "status": "done",
                    "download_url": f"/api/podcast/download/{session_id}",
                    "format": "webm",
                    "bytes": total_bytes,
                    "turns": turn_count,
                }
            ),
        )
    except Exception as e:
        # Real failure -> mark failed, emit error event. Never stub.
        msg = f"{type(e).__name__}: {e}"
        update_status(session_id, "failed", error=msg)
        yield _sse("error", json.dumps({"status": "failed", "message": msg}))
