"""Free speech synthesis via edge-tts.

Speaks teaching text / hints. If edge-tts is unreachable (offline), callers
should fall back to showing the text. This module raises on failure so the
HTTP layer can return 503.
"""

from __future__ import annotations

import io

import edge_tts


async def speak_mp3(text: str, voice: str = "en-US-AriaNeural") -> bytes:
    """Return MP3 audio bytes for the given text using edge-tts (free)."""
    if not text or not text.strip():
        raise ValueError("empty text")
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            data = chunk.get("data")
            if data:
                buf.write(data)
    data = buf.getvalue()
    if not data:
        raise RuntimeError("edge-tts returned empty audio")
    return data
