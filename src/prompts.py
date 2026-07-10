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


SYSTEM_PROMPT = """You are writing a natural, unscripted-feeling podcast conversation between two or three hosts.

TOPIC: {topic}

HOSTS:
{host_lines}

STYLE — make it sound like real people talking, not a scripted panel:
- Each host has a distinct voice and reacts to what the OTHERS just said. Build on their points, push back, laugh, riff, change the subject slightly, bring it back.
- Lines vary in length: sometimes a short interjection ("Right, exactly."), sometimes a 2-3 sentence riff. Do NOT cap every line to one sentence.
- Speakers do NOT take strict turns. A host may respond twice in a row if it fits, or jump in. Keep it lively but coherent.
- Use contractions, casual phrasing, the occasional "uh"/"y'know"/"so" — but never stage directions, brackets, or actions.
- Stay on the topic broadly, but let the conversation wander naturally like humans do.
- End only when the discussion has clearly landed (a natural sign-off or wrap-up), then output exactly: [END]
- Aim for roughly {max_turns} lines total, but end early if it feels done.

OUTPUT FORMAT — one line per response, exactly:
  <HostName>: <the line>

Write the ENTIRE conversation now (all lines, ending with [END]).
"""


def build_script_prompt(topic: str, hosts: list[Host], max_turns: int) -> str:
    host_lines = "\n".join(f"- {h.name}: {h.persona}" for h in hosts)
    return SYSTEM_PROMPT.format(topic=topic, host_lines=host_lines, max_turns=max_turns)
