"""Dialogue generator: a full podcast script from Gemini in ONE call (cost-efficient).

We ask Gemini for the entire conversation in a single request, then parse the
lines and yield them one at a time so downstream TTS + live streaming still work
line-by-line. This cuts Gemini usage from ~1 call/line (12-24/episode) to 1/episode,
which matters under a tight monthly spend cap.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import google.generativeai as genai

from ..config import config
from ..prompts import build_script_prompt, get_hosts

_LINE_RE = re.compile(r"^\s*([A-Za-z][\w\- ]{0,30}?)\s*:\s*(.+)$", re.DOTALL)
_END_MARKER = "[END]"


@dataclass
class Turn:
    speaker: str
    text: str


class DialogueError(RuntimeError):
    pass


def _configure() -> None:
    if not config.gemini_key_present:
        raise DialogueError(
            "AGENT_GEMINI_API_KEY is missing. Set it in the repo-root .env and restart."
        )
    genai.configure(api_key=config.GEMINI_API_KEY)


def parse_script(raw: str, name_to_id: dict[str, str]) -> list[Turn]:
    """Parse a full 'Name: line' script into Turn objects (stops at [END])."""
    turns: list[Turn] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith(_END_MARKER):
            break
        m = _LINE_RE.match(line)
        if not m:
            continue
        spoken, text = m.group(1).strip(), m.group(2).strip()
        for name, hid in name_to_id.items():
            if name.lower() == spoken.lower():
                turns.append(Turn(speaker=hid, text=text))
                break
    return turns


async def stream_turns(topic: str, host_ids: list[str]):
    """Yield Turn objects one per line. The script is generated in a SINGLE
    Gemini call (cost-efficient under a spend cap); lines are then streamed."""
    _configure()
    hosts = get_hosts(host_ids)
    name_to_id = {h.name: h.id for h in hosts}
    model = genai.GenerativeModel(config.GEMINI_MODEL)

    try:
        resp = model.generate_content(
            build_script_prompt(topic, hosts, config.MAX_TURNS),
            generation_config={"max_output_tokens": 2000, "temperature": 0.9},
        )
    except Exception as e:  # surface real Gemini failures; never silently stub
        raise DialogueError(f"Gemini call failed: {type(e).__name__}") from e

    raw = (resp.text or "").strip()
    turns = parse_script(raw, name_to_id)
    if not turns:
        raise DialogueError("Gemini produced no usable dialogue turns.")
    for turn in turns:
        yield turn
