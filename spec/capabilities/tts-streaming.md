# Capability: Real-Time TTS Streaming

## What It Does

Converts each dialogue line into real audio (edge-tts, no API key) with a distinct voice per host,
and streams the audio chunks to the browser as they are synthesized.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| Turn (speaker, text) | object | dialogue node | yes |
| voice | string | host persona mapping | yes |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| mp3 audio bytes | bytes | SSE stream + session file |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| edge-tts | `Communicate(text, voice).stream()` | fatal → SSE `error` event, session `failed` |

## Business Rules

- Each host maps to a fixed, distinct edge-tts voice (see `src/prompts.py` cast).
- Audio is emitted chunk-by-chunk as synthesized (real-time), not buffered until the end.
- Chunks are also appended to the session's output file for the final download.

## Success Criteria

- [ ] A real edge-tts call returns non-empty mp3 bytes for a given line.
- [ ] Different hosts produce different voices (distinct voice ids; asserted by config).
- [ ] Chunks are delivered over SSE as they are produced (asserted by the stream test).
