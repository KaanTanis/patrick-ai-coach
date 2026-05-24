from typing import Literal

from pydantic import BaseModel, Field


class ExtractedMemoryItem(BaseModel):
    content: str
    memory_type: Literal[
        "fact", "trigger", "pattern", "goal", "relapse", "schedule", "episode", "reminder"
    ] = "fact"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    deadline: str | None = None
    frequency: str | None = None
    success_signal: str | None = None


class MemoryExtracted(BaseModel):
    memories: list[ExtractedMemoryItem] = Field(default_factory=list)


class UserSchedule(BaseModel):
    current_shift: str | None = None
    next_shift_start: str | None = None
    next_shift_end: str | None = None
    sleep_window: str | None = None
    active_hours_note: str | None = None
    timezone_notes: str | None = None


class ProfileUpdateResult(BaseModel):
    context_summary: str
    schedule: UserSchedule
