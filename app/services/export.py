import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories import (
    CheckInRepository,
    ConversationRepository,
    InsightRepository,
    MealRepository,
    MemoryRepository,
    SmokingEventRepository,
    UserRepository,
    WorkoutRepository,
)


class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_all(self, user_id: int) -> dict[str, Any]:
        check_ins = CheckInRepository(self.session)
        meals = MealRepository(self.session)
        smoking = SmokingEventRepository(self.session)
        workouts = WorkoutRepository(self.session)
        conversations = ConversationRepository(self.session)
        memories = MemoryRepository(self.session)
        insights = InsightRepository(self.session)
        users = UserRepository(self.session)

        user = await self.session.get(User, user_id)

        return {
            "user": {
                "telegram_id": user.telegram_id if user else None,
                "name": user.name if user else None,
                "personality_key": user.personality_key if user else None,
                "goals": user.goals if user else {},
            },
            "check_ins": [
                {
                    "date": str(c.date),
                    "mood": c.mood,
                    "sleep_quality": c.sleep_quality,
                    "energy": c.energy,
                    "smoking_craving": c.smoking_craving,
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
            "smoking_events": [
                {
                    "type": e.event_type,
                    "intensity": e.intensity,
                    "note": e.trigger_note,
                    "occurred_at": e.occurred_at.isoformat(),
                }
                for e in await smoking.get_recent(user_id, days=365)
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
                {"type": m.memory_type, "content": m.content, "importance": m.importance}
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
                    "created_at": c.created_at.isoformat(),
                }
                for c in await conversations.get_recent(user_id, limit=500)
            ],
        }

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
        from datetime import datetime, timezone

        return await self.conversations.delete_older_than(datetime.now(timezone.utc))
