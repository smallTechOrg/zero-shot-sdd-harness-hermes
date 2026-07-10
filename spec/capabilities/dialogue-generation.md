# Capability: Live Dialogue Generation

## What It Does

Generates a coherent, multi-host podcast conversation turn-by-turn from a one-line topic, using the
real Gemini API, maintaining speaker order and on-topic coherence.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| topic | string | user request | yes |
| hosts | list[Host] | user selection | yes |
| turns_so_far | list[Turn] | in-process state | no |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| Turn (speaker, text) | object | TTS node + session transcript |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Gemini | `generate_content` (one line per call) | fatal → SSE `error` event, session `failed` |

## Business Rules

- Exactly the selected hosts speak, alternating in a stable order.
- Each Gemini call returns ONE line (`SPEAKER: text`) to enable per-line streaming.
- Episode ends at `MAX_TURNS` (default 12) or Gemini `[END]` marker.
- No cross-session memory: each run starts fresh.

## Success Criteria

- [ ] A real Gemini call returns a parseable `SPEAKER: text` line for the requested topic.
- [ ] Speakers alternate and stay within the selected cast.
- [ ] Conversation remains coherent and on-topic across turns (asserted in tests by content checks).
