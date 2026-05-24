from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MemoryType
from app.repositories import CheckInRepository, MealRepository, MemoryRepository
from app.repositories.philosophy import (
    DreamRepository,
    EmotionRepository,
    ShadowRepository,
    StoicRitualRepository,
)


class TimelineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.check_ins = CheckInRepository(session)
        self.meals = MealRepository(session)
        self.memories = MemoryRepository(session)
        self.dreams = DreamRepository(session)
        self.shadows = ShadowRepository(session)
        self.stoic = StoicRitualRepository(session)
        self.emotions = EmotionRepository(session)

    async def build(self, user_id: int, days: int = 30) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        events: list[dict[str, Any]] = []

        for c in await self.check_ins.get_recent(user_id, days=days):
            events.append(
                {
                    "at": datetime.combine(c.date, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat(),
                    "type": "checkin",
                    "title": f"Rapor {c.date}",
                    "detail": {
                        "mood": c.mood,
                        "stress": c.stress,
                        "energy": c.energy,
                        "workout_done": c.workout_done,
                    },
                }
            )

        for m in await self.meals.get_recent(user_id, limit=100):
            if m.logged_at >= since:
                events.append(
                    {
                        "at": m.logged_at.isoformat(),
                        "type": "meal",
                        "title": (m.ai_analysis or "Öğün")[:60],
                        "detail": {"calories": m.estimated_calories},
                    }
                )

        for mem in await self.memories.list_all(user_id):
            if mem.created_at < since:
                continue
            if mem.memory_type == MemoryType.RELAPSE:
                events.append(
                    {
                        "at": mem.created_at.isoformat(),
                        "type": "setback",
                        "title": "Gerileme",
                        "detail": {"content": mem.content[:200]},
                    }
                )
            elif mem.memory_type in {MemoryType.GOAL, MemoryType.REMINDER}:
                events.append(
                    {
                        "at": mem.created_at.isoformat(),
                        "type": mem.memory_type,
                        "title": mem.content[:80],
                        "detail": mem.metadata_ or {},
                    }
                )
            elif mem.memory_type == MemoryType.EPISODE:
                meta = mem.metadata_ or {}
                events.append(
                    {
                        "at": mem.created_at.isoformat(),
                        "type": meta.get("type", "episode"),
                        "title": mem.content[:80],
                        "detail": meta,
                    }
                )

        for d in await self.dreams.get_recent(user_id, days=days, limit=50):
            events.append(
                {
                    "at": d.logged_at.isoformat(),
                    "type": "dream",
                    "title": "Rüya",
                    "detail": {"mood": d.mood, "content": d.content[:120]},
                }
            )

        for s in await self.shadows.get_recent(user_id, days=days, limit=50):
            events.append(
                {
                    "at": s.logged_at.isoformat(),
                    "type": "shadow",
                    "title": "Gölge notu",
                    "detail": {"content": s.content[:120]},
                }
            )

        for r in await self.stoic.get_recent(user_id, days=days, limit=50):
            events.append(
                {
                    "at": r.logged_at.isoformat(),
                    "type": "stoic",
                    "title": f"Stoik {r.ritual_type}",
                    "detail": {},
                }
            )

        for e in await self.emotions.get_recent(user_id, days=days, limit=50):
            events.append(
                {
                    "at": e.logged_at.isoformat(),
                    "type": "emotion",
                    "title": e.emotion,
                    "detail": {"intensity": e.intensity},
                }
            )

        events.sort(key=lambda x: x["at"], reverse=True)
        return events[:200]

    async def get_weekly_summary(self, user_id: int) -> str | None:
        episodes = await self.memories.get_recent_episodes(user_id, days=14, limit=10)
        for ep in reversed(episodes):
            meta = ep.metadata_ or {}
            if meta.get("type") in {"weekly_reflection", "weekly_goal_review", "first_week_summary"}:
                return ep.content
        return None

    async def get_correlation_flags(self, user_id: int) -> list[dict[str, Any]]:
        from app.ai.behavioral.analyzer import BehavioralAnalyzer

        analyzer = BehavioralAnalyzer(self.session)
        return await analyzer.detect_patterns(user_id)
