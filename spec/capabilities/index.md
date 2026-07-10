# Capabilities Index

> The spec-writer sub-agent creates one file per capability in this directory.

## Capabilities in This Project

| Capability | File |
|-----------|------|
| Live Dialogue Generation | [dialogue-generation.md](dialogue-generation.md) |
| Real-Time TTS Streaming | [tts-streaming.md](tts-streaming.md) |
| Session Persistence & Download | [session-persistence.md](session-persistence.md) |

## How to Add a New Capability

Run `/zero-shot-build [description]` on the existing spec. The spec-writer sub-agent will:
1. Create a new file in this directory (`<name>.md`, no number prefix)
2. Update this index
3. Flag any dependencies on existing capabilities
4. Self-review that it fits the architecture and data model before returning
