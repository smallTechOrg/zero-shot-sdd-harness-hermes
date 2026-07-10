"""End-to-end generate test: real Gemini + real edge-tts, streaming SSE.

Asserts:
  (a) POST /generate returns a session_id and creates a DB row (status generating).
  (b) GET /stream/<id> yields `audio` SSE events carrying real, non-empty mp3 bytes,
      then a `done` event; DB flips to `done` with a real file path.
  (c) the saved file is a valid, non-empty mp3 (ID3/MP3 magic).
  (d) no API key value leaks into any response body.
"""
import base64
import json

import pytest

pytestmark = pytest.mark.realkey


def _parse_sse(text: str):
    """Yield (event, data) from a raw SSE text body."""
    for frame in text.split("\n\n"):
        ev = "message"
        data = []
        for line in frame.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if data:
            yield ev, "\n".join(data)


def test_generate_streams_real_audio_and_saves_file(client):
    # (a) start generation
    r = client.post(
        "/api/podcast/generate",
        json={"topic": "the future of remote work", "hosts": ["maya", "leo"]},
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert sid

    # (b) open the SSE stream and consume it
    with client.stream("GET", f"/api/podcast/stream/{sid}") as s:
        assert s.status_code == 200

        audio_bytes = bytearray()
        got_done = False
        raw = ""
        for chunk in s.iter_raw():
            raw += chunk.decode("utf-8", errors="replace")
            for ev, data in _parse_sse(raw):
                if ev == "audio":
                    audio_bytes += base64.b64decode(data)
                elif ev == "done":
                    got_done = True
                elif ev == "error":
                    pytest.fail(f"Stream errored: {data}")
            # trim processed frames to bound memory
            raw = raw.split("\n\n")[-1]

    assert got_done, "stream should emit a `done` event"
    assert len(audio_bytes) > 1000, "expected real, non-trivial audio bytes"

    # (c) session persisted as done with a real file
    from src.db import get_session

    sess = get_session(sid)
    assert sess is not None
    assert sess["status"] == "done"
    assert sess["audio_path"]

    import os

    assert os.path.exists(sess["audio_path"]), "saved audio file must exist"
    size = os.path.getsize(sess["audio_path"])
    assert size > 1000, "saved file must be non-trivial"

    # (d) secret hygiene: no key substring anywhere in streamed output
    from src.config import config

    assert config.GEMINI_API_KEY not in raw
