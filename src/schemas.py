"""Pydantic request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    student_id: str = Field(min_length=1)
    clefs: list[str] = Field(default_factory=lambda: ["treble"])
    display_name: str | None = None


class CheckRequest(BaseModel):
    student_answer: str = Field(min_length=1)


class NextRequest(BaseModel):
    drill_id: str
    student_id: str


class TeachingOut(BaseModel):
    text: str
    tokens: dict
    model: str
    used_fallback: bool


class ExerciseOut(BaseModel):
    id: str
    midi: int
    correct_name: str
    clef: str
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
