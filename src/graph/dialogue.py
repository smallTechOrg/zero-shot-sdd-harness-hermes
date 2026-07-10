"""Dialogue generator: turn-by-turn podcast script via Gemini (real API)."""
from __future__ import annotations

import re
from dataclasses import dataclass

import google.generativeai as genai

from ..config import config
from ..prompts import build_system_prompt, get_hosts, USER_TURN_PROMPT

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


def parse_line(raw: str, name_to_id: dict[str, str]) -> Turn | None:
    """Parse a 'Name: text' line, mapping the spoken name back to a host id.

    Returns None if the line is the [END] marker or unparseable.
    """
    raw = raw.strip()
    if not raw:
        return None
    if raw.upper().startswith(_END_MARKER):
        return None  # signal end
    m = _LINE_RE.match(raw)
    if not m:
        return None
    spoken, text = m.group(1).strip(), m.group(2).strip()
    # Match spoken name to a host by case-insensitive name; return the id.
    for name, hid in name_to_id.items():
        if name.lower() == spoken.lower():
            return Turn(speaker=hid, text=text)
    return None


async def stream_turns(topic: str, host_ids: list[str]):
    """Async generator yielding Turn objects, one per Gemini call.

    Maintains the running transcript in the prompt so the conversation stays
    coherent. Alternates speakers. Stops at MAX_TURNS or an [END] marker.
    """
    _configure()
    hosts = get_hosts(host_ids)
    name_to_id = {h.name: h.id for h in hosts}
    model = genai.GenerativeModel(config.GEMINI_MODEL)

    history: list[str] = []
    sys_prompt = build_system_prompt(topic, hosts)

    for i in range(config.MAX_TURNS):
        try:
            resp = model.generate_content(
                [sys_prompt] + history + [USER_TURN_PROMPT],
                generation_config={"max_output_tokens": 400, "temperature": 0.9},
            )
        except Exception as e:  # surface real Gemini failures; never silently stub
            raise DialogueError(f"Gemini call failed: {type(e).__name__}") from e

        raw = (resp.text or "").strip()
        turn = parse_line(raw, name_to_id)
        if turn is None:
            # [END] or unparseable -> stop
            break
        history.append(raw)
        yield turn
