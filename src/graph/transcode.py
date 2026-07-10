"""Transcode edge-tts MP3 chunks to WebM/Opus for live browser playback.

edge-tts emits ADTS MP3 frames, but MediaSource in Chrome does NOT support
`audio/mpeg`. It DOES support `audio/webm;codecs=opus`. We convert each MP3
chunk to a self-contained WebM segment (one utterance) so the frontend can
append them sequentially to a MediaSource SourceBuffer and play live.

Each conversion is a full, valid WebM file => safe to append in `sequence` mode.
"""
from __future__ import annotations

import subprocess

WEBM_MIME = "audio/webm;codecs=opus"


def mp3_chunk_to_webm(mp3: bytes) -> bytes:
    """Convert a raw MP3 chunk (bytes) to a standalone WebM/Opus segment."""
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",            # read mp3 from stdin
            "-c:a", "libopus",         # opus codec
            "-b:a", "48k",
            "-application", "voip",
            "-f", "webm",              # WebM container
            "pipe:1",                  # write webm to stdout
        ],
        input=mp3,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return proc.stdout
