"""Fixed host cast + system prompt for dialogue generation.

The cast is FIXED for v1: the user picks 2–3 of these at generate time. Each host
maps to a distinct, free edge-tts voice. Voices are real Microsoft TTS voice IDs.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import config


@dataclass(frozen=True)
class Host:
    id: str
    name: str
    voice: str          # edge-tts voice id
    persona: str        # one-line description fed to the dialogue prompt


# Fixed cast. Distinct voices (male/female, different locales) for clear separation.
CAST: dict[str, Host] = {
    "maya": Host(
        id="maya",
        name="Maya",
        voice="en-US-AriaNeural",          # female, warm
        persona="a curious, upbeat journalist who asks sharp follow-ups",
    ),
    "leo": Host(
        id="leo",
        name="Leo",
        voice="en-US-GuyNeural",           # male, calm
        persona="a measured industry analyst who grounds ideas in evidence",
    ),
    "nova": Host(
        id="nova",
        name="Nova",
        voice="en-GB-SoniaNeural",         # female, British, bright
        persona="a playful futurist who throws in wild but plausible scenarios",
    ),
}


def get_hosts(ids: list[str]) -> list[Host]:
    """Resolve host ids to Host objects; raises KeyError on unknown id."""
    return [CAST[i] for i in ids]


SYSTEM_PROMPT = """You are writing a natural, unscripted-feeling podcast conversation.

TOPIC: {topic}

HOSTS (in speaking order, alternate strictly between them):
{host_lines}

RULES:
- Output EXACTLY ONE spoken line per response, in this format:
  <HostName>: <one line of natural dialogue>
- Alternate speakers each turn (do not let one host dominate).
- Stay on topic. Be conversational, concise (1–2 sentences per line).
- Do NOT use stage directions, brackets, or labels other than the "Name:" prefix.
- When the conversation has naturally wrapped up (a clear conclusion), output exactly:
  [END]
- Keep the total episode to about {max_turns} lines unless you reach a natural end first.
"""


def build_system_prompt(topic: str, hosts: list[Host]) -> str:
    host_lines = "\n".join(f"- {h.name}: {h.persona}" for h in hosts)
    return SYSTEM_PROMPT.format(
        topic=topic, host_lines=host_lines, max_turns=config.MAX_TURNS
    )


USER_TURN_PROMPT = (
    "Continue the conversation. Output the next speaker's single line now "
    "(format 'Name: line'), or '[END]' if it is naturally concluded."
)
