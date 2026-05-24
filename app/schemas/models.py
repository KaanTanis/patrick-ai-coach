from typing import Any

from pydantic import BaseModel, Field


class CheckInCreate(BaseModel):
    mood: int | None = Field(None, ge=1, le=10)
    sleep_quality: int | None = Field(None, ge=1, le=10)
    energy: int | None = Field(None, ge=1, le=10)
    smoking_craving: int | None = Field(None, ge=1, le=10)
    workout_done: bool | None = None
    workout_type: str | None = None
    stress: int | None = Field(None, ge=1, le=10)
    weight: float | None = None
    motivation: int | None = Field(None, ge=1, le=10)
    notes: str | None = None


class FoodAnalysisResult(BaseModel):
    estimated_calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    portion_description: str
    confidence: str
    healthier_swap: str
    conversational_response: str


class BehavioralInsightCreate(BaseModel):
    insight_type: str
    title: str
    body: str
    evidence: dict[str, Any] | None = None
    confidence: float = 0.7


class OrchestratorResponse(BaseModel):
    text: str
    session_id: str
    intent: str
