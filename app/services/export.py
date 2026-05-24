import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BehavioralInsight,
    CheckIn,
    Conversation,
    DreamEntry,
    EmotionCheckin,
    Meal,
    Memory,
    ShadowNote,
    StoicRitual,
    ThoughtRecord,
    User,
    Workout,
)
from app.repositories import (
    CheckInRepository,
    ConversationRepository,
    InsightRepository,
    MealRepository,
    MemoryRepository,
    WorkoutRepository,
)
from app.repositories.philosophy import (
    DreamRepository,
    EmotionRepository,
    ShadowRepository,
    StoicRitualRepository,
    ThoughtRepository,
)
from app.services.chat_session import clear_session


class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_all(self, user_id: int) -> dict[str, Any]:
        check_ins = CheckInRepository(self.session)
        meals = MealRepository(self.session)
        workouts = WorkoutRepository(self.session)
        conversations = ConversationRepository(self.session)
        memories = MemoryRepository(self.session)
        insights = InsightRepository(self.session)
        dreams = DreamRepository(self.session)
        shadows = ShadowRepository(self.session)
        thoughts = ThoughtRepository(self.session)
        stoic = StoicRitualRepository(self.session)
        emotions = EmotionRepository(self.session)

        user = await self.session.get(User, user_id)
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": {
                "telegram_id": user.telegram_id if user else None,
                "name": user.name if user else None,
                "personality_key": user.personality_key if user else None,
                "goals": user.goals if user else {},
                "timezone": user.timezone if user else None,
                "context_summary": user.context_summary if user else None,
                "schedule": user.schedule if user else {},
                "preferences": user.preferences if user else {},
            },
            "check_ins": [
                {
                    "date": str(c.date),
                    "mood": c.mood,
                    "sleep_quality": c.sleep_quality,
                    "energy": c.energy,
                    "workout_done": c.workout_done,
                    "stress": c.stress,
                    "weight": float(c.weight) if c.weight else None,
                    "motivation": c.motivation,
                    "notes": c.notes,
                }
                for c in await check_ins.get_recent(user_id, days=365)
            ],
            "meals": [
                {
                    "logged_at": m.logged_at.isoformat(),
                    "calories": m.estimated_calories,
                    "analysis": m.ai_analysis,
                }
                for m in await meals.get_recent(user_id, limit=500)
            ],
            "workouts": [
                {
                    "type": w.type,
                    "duration_min": w.duration_min,
                    "completed": w.completed,
                    "logged_at": w.logged_at.isoformat(),
                }
                for w in await workouts.get_recent(user_id, days=365)
            ],
            "memories": [
                {
                    "type": m.memory_type,
                    "content": m.content,
                    "importance": m.importance,
                    "created_at": m.created_at.isoformat(),
                }
                for m in await memories.list_all(user_id)
            ],
            "insights": [
                {"title": i.title, "body": i.body, "type": i.insight_type}
                for i in await insights.get_active(user_id, limit=100)
            ],
            "conversations": [
                {
                    "session_id": c.session_id,
                    "role": c.role,
                    "content": c.content,
                    "token_count": c.token_count,
                    "created_at": c.created_at.isoformat(),
                }
                for c in await conversations.get_recent(user_id, limit=500)
            ],
            "dream_entries": [
                {
                    "content": d.content,
                    "mood": d.mood,
                    "logged_at": d.logged_at.isoformat(),
                }
                for d in await dreams.get_recent(user_id, days=365, limit=200)
            ],
            "shadow_notes": [
                {"content": s.content, "logged_at": s.logged_at.isoformat()}
                for s in await shadows.get_recent(user_id, days=365, limit=200)
            ],
            "thought_records": [
                {
                    "situation": t.situation,
                    "emotion": t.emotion,
                    "logged_at": t.logged_at.isoformat(),
                }
                for t in await thoughts.get_recent(user_id, days=365, limit=200)
            ],
            "stoic_rituals": [
                {
                    "type": r.ritual_type,
                    "logged_at": r.logged_at.isoformat(),
                }
                for r in await stoic.get_recent(user_id, days=365, limit=200)
            ],
            "emotion_checkins": [
                {
                    "emotion": e.emotion,
                    "intensity": e.intensity,
                    "logged_at": e.logged_at.isoformat(),
                }
                for e in await emotions.get_recent(user_id, days=365, limit=200)
            ],
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        payload["checksum_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        return payload

    async def export_json(self, user_id: int) -> str:
        return json.dumps(await self.export_all(user_id), indent=2, default=str)


class ForgetService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memories = MemoryRepository(session)
        self.conversations = ConversationRepository(session)

    async def forget_memories(self, user_id: int, memory_type: str | None = None) -> int:
        return await self.memories.delete_by_type(user_id, memory_type)

    async def forget_conversations(self, user_id: int) -> int:
        return await self.conversations.delete_older_than(datetime.now(timezone.utc))


class ErasureService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.meals = MealRepository(session)

    async def erase_all(self, user_id: int, telegram_id: int) -> dict[str, int]:
        meal_list = await self.meals.get_recent(user_id, limit=10000)
        photos_removed = 0
        for meal in meal_list:
            if meal.photo_path:
                path = Path(meal.photo_path)
                if path.exists():
                    path.unlink()
                    photos_removed += 1

        tables = [
            (Conversation, Conversation.user_id),
            (Memory, Memory.user_id),
            (BehavioralInsight, BehavioralInsight.user_id),
            (DreamEntry, DreamEntry.user_id),
            (ShadowNote, ShadowNote.user_id),
            (ThoughtRecord, ThoughtRecord.user_id),
            (StoicRitual, StoicRitual.user_id),
            (EmotionCheckin, EmotionCheckin.user_id),
            (CheckIn, CheckIn.user_id),
            (Meal, Meal.user_id),
            (Workout, Workout.user_id),
            (User, User.id),
        ]
        counts: dict[str, int] = {"photos": photos_removed}
        for model, column in tables:
            name = model.__tablename__
            result = await self.session.execute(delete(model).where(column == user_id))
            counts[name] = result.rowcount or 0

        await clear_session(telegram_id)
        return counts
