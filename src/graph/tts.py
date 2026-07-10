"""TTS node: real audio via edge-tts (free, no API key), distinct voice per host."""
from __future__ import annotations

import edge_tts

from ..prompts import get_hosts


class TTSError(RuntimeError):
    pass


async def synthesize(text: str, voice: str):
    """Async generator yielding raw mp3 chunks (bytes) for `text` in `voice`."""
    communicate = edge_tts.Communicate(text, voice)
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except Exception as e:
        raise TTSError(f"edge-tts failed for voice {voice}: {type(e).__name__}") from e


async def synthesize_turn(text: str, host_id: str):
    """Yield audio chunks for a host's line using that host's assigned voice."""
    host = get_hosts([host_id])[0]
    async for chunk in synthesize(text, host.voice):
        yield chunk
