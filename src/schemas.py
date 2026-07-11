"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    student_id: str = Field(min_length=1)
    clefs: list[str] = Field(default_factory=lambda: ["treble"])
    display_name: str | None = None
    drill_type: str = "note"  # "note" | "rhythm"


class CheckRequest(BaseModel):
    student_answer: str = Field(min_length=1)


class NextRequest(BaseModel):
    drill_id: str
    student_id: str
    drill_type: str = "note"


class TeachingOut(BaseModel):
    text: str
    tokens: dict
    model: str
    used_fallback: bool


class ExerciseOut(BaseModel):
    id: str
    drill_id: str | None = None
    type: str = "note"
    midi: int | None = None
    correct_name: str
    clef: str | None = None
    label: str | None = None
    is_rest: bool | None = None
    staff_svg: str
    options: list[str]


class StartResponse(BaseModel):
    drill_id: str
    teaching: TeachingOut
    exercise: ExerciseOut


class CheckResponse(BaseModel):
    correct: bool
    computed_name: str
    hint: str | None
    revealed: bool


class MasteryRow(BaseModel):
    topic: str
    weight: float
    attempts: int
    correct: int


class SchedRow(BaseModel):
    item_id: str
    box: int
    streak: int
    lapses: int
    due_at: float
    last_seen: float
    last_correct: bool


class CurriculumTopic(BaseModel):
    id: str
    label: str
    type: str
    clefs: list[str]
    items: list[str]
    goal: str


class SuggestOut(BaseModel):
    topic_id: str | None = None
    label: str | None = None
    type: str | None = None
    drill_type: str | None = None
    reason: str | None = None
    weak_item: str | None = None
    avg_box: float | None = None
    avg_weight: float | None = None
