from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MemoryType(StrEnum):
    FACT = "fact"
    TRIGGER = "trigger"
    PATTERN = "pattern"
    GOAL = "goal"
    INSIGHT = "insight"
    RELAPSE = "relapse"
    SCHEDULE = "schedule"
    EPISODE = "episode"
    SYMBOL = "symbol"
    REMINDER = "reminder"


class MemorySource(StrEnum):
    EXTRACTED = "extracted"
    MANUAL = "manual"
    ANALYSIS = "analysis"


class InsightType(StrEnum):
    CORRELATION = "correlation"
    TREND = "trend"
    WARNING = "warning"
    CELEBRATION = "celebration"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    personality_key: Mapped[str] = mapped_column(String(50), default="companion")
    goals: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Istanbul")
    context_summary: Mapped[str | None] = mapped_column(Text)
    schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_proactive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nudges_today_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    nudges_today_date: Mapped[date | None] = mapped_column(Date)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    check_ins: Mapped[list["CheckIn"]] = relationship(back_populates="user")
    meals: Mapped[list["Meal"]] = relationship(back_populates="user")
    workouts: Mapped[list["Workout"]] = relationship(back_populates="user")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    memories: Mapped[list["Memory"]] = relationship(back_populates="user")
    insights: Mapped[list["BehavioralInsight"]] = relationship(back_populates="user")
    dream_entries: Mapped[list["DreamEntry"]] = relationship(back_populates="user")
    shadow_notes: Mapped[list["ShadowNote"]] = relationship(back_populates="user")
    thought_records: Mapped[list["ThoughtRecord"]] = relationship(back_populates="user")
    stoic_rituals: Mapped[list["StoicRitual"]] = relationship(back_populates="user")
    emotion_checkins: Mapped[list["EmotionCheckin"]] = relationship(back_populates="user")


class CheckIn(Base):
    __tablename__ = "check_ins"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_check_ins_user_date"),
        Index("ix_check_ins_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    mood: Mapped[int | None] = mapped_column(SmallInteger)
    sleep_quality: Mapped[int | None] = mapped_column(SmallInteger)
    energy: Mapped[int | None] = mapped_column(SmallInteger)
    workout_done: Mapped[bool | None] = mapped_column(Boolean)
    workout_type: Mapped[str | None] = mapped_column(Text)
    stress: Mapped[int | None] = mapped_column(SmallInteger)
    weight: Mapped[float | None] = mapped_column(Numeric(6, 2))
    motivation: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="check_ins")


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    photo_path: Mapped[str | None] = mapped_column(Text)
    estimated_calories: Mapped[int | None] = mapped_column(Integer)
    protein_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    carbs_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    fat_g: Mapped[float | None] = mapped_column(Numeric(6, 1))
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    raw_vision: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="meals")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str | None] = mapped_column(String(100))
    duration_min: Mapped[int | None] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="workouts")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_session", "user_id", "session_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="conversations")


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (Index("ix_memories_user_type_importance", "user_id", "memory_type", "importance"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(20), default=MemorySource.EXTRACTED)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="memories")
    embedding: Mapped["MemoryEmbedding | None"] = relationship(
        back_populates="memory", uselist=False, cascade="all, delete-orphan"
    )


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    memory_id: Mapped[int] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    memory: Mapped["Memory"] = relationship(back_populates="embedding")


class BehavioralInsight(Base):
    __tablename__ = "behavioral_insights"
    __table_args__ = (Index("ix_insights_user_surfaced", "user_id", "surfaced_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    insight_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    surfaced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="insights")


class PersonalityProfile(Base):
    __tablename__ = "personality_profiles"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tone_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class DreamEntry(Base):
    __tablename__ = "dream_entries"
    __table_args__ = (Index("ix_dream_entries_user_logged", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    symbols: Mapped[list[str] | None] = mapped_column(JSONB)
    mood: Mapped[str | None] = mapped_column(String(100))
    ai_interpretation: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="dream_entries")


class ShadowNote(Base):
    __tablename__ = "shadow_notes"
    __table_args__ = (Index("ix_shadow_notes_user_logged", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ai_reflection: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="shadow_notes")


class ThoughtRecord(Base):
    __tablename__ = "thought_records"
    __table_args__ = (Index("ix_thought_records_user_logged", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    situation: Mapped[str | None] = mapped_column(Text)
    automatic_thought: Mapped[str | None] = mapped_column(Text)
    emotion: Mapped[str | None] = mapped_column(String(100))
    emotion_intensity: Mapped[int | None] = mapped_column(SmallInteger)
    evidence_for: Mapped[str | None] = mapped_column(Text)
    evidence_against: Mapped[str | None] = mapped_column(Text)
    balanced_thought: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="thought_records")


class StoicRitual(Base):
    __tablename__ = "stoic_rituals"
    __table_args__ = (Index("ix_stoic_rituals_user_type", "user_id", "ritual_type", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ritual_type: Mapped[str] = mapped_column(String(20), nullable=False)
    control_items: Mapped[list[str] | None] = mapped_column(JSONB)
    premeditatio: Mapped[str | None] = mapped_column(Text)
    virtue_intention: Mapped[str | None] = mapped_column(Text)
    evening_good: Mapped[str | None] = mapped_column(Text)
    evening_hard: Mapped[str | None] = mapped_column(Text)
    dichotomy_audit: Mapped[str | None] = mapped_column(Text)
    tomorrow_intention: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="stoic_rituals")


class EmotionCheckin(Base):
    __tablename__ = "emotion_checkins"
    __table_args__ = (Index("ix_emotion_checkins_user_logged", "user_id", "logged_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    emotion: Mapped[str] = mapped_column(String(100), nullable=False)
    intensity: Mapped[int | None] = mapped_column(SmallInteger)
    body_sensation: Mapped[str | None] = mapped_column(Text)
    ai_reflection: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="emotion_checkins")
