from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BehavioralInsight,
    CheckIn,
    Conversation,
    Meal,
    Memory,
    MemoryEmbedding,
    MemoryType,
    PersonalityProfile,
    User,
    Workout,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, name: str | None = None) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user
        user = User(telegram_id=telegram_id, name=name, personality_key="companion")
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_personality(self, user_id: int, personality_key: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(personality_key=personality_key)
        )

    async def update_goals(self, user_id: int, goals: dict[str, Any]) -> None:
        await self.session.execute(update(User).where(User.id == user_id).values(goals=goals))

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def update_context(
        self,
        user_id: int,
        context_summary: str,
        schedule: dict[str, Any] | None = None,
    ) -> None:
        values: dict[str, Any] = {"context_summary": context_summary}
        if schedule is not None:
            values["schedule"] = schedule
        await self.session.execute(update(User).where(User.id == user_id).values(**values))

    async def record_proactive_nudge(self, user_id: int, today: date) -> None:
        user = await self.get_by_id(user_id)
        if not user:
            return
        count = 1
        if user.nudges_today_date == today:
            count = (user.nudges_today_count or 0) + 1
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_proactive_at=datetime.now(timezone.utc),
                nudges_today_count=count,
                nudges_today_date=today,
            )
        )


class CheckInRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, user_id: int, checkin_date: date, data: dict[str, Any]) -> CheckIn:
        result = await self.session.execute(
            select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.date == checkin_date)
        )
        check_in = result.scalar_one_or_none()
        if check_in:
            for key, value in data.items():
                setattr(check_in, key, value)
        else:
            check_in = CheckIn(user_id=user_id, date=checkin_date, **data)
            self.session.add(check_in)
        await self.session.flush()
        return check_in

    async def get_recent(self, user_id: int, days: int = 7) -> list[CheckIn]:
        since = date.today() - timedelta(days=days)
        result = await self.session.execute(
            select(CheckIn)
            .where(CheckIn.user_id == user_id, CheckIn.date >= since)
            .order_by(CheckIn.date.desc())
        )
        return list(result.scalars().all())

    async def get_by_date(self, user_id: int, checkin_date: date) -> CheckIn | None:
        result = await self.session.execute(
            select(CheckIn).where(CheckIn.user_id == user_id, CheckIn.date == checkin_date)
        )
        return result.scalar_one_or_none()


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(
        self,
        user_id: int,
        session_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
    ) -> Conversation:
        message = Conversation(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_recent(
        self, user_id: int, session_id: str | None = None, limit: int = 20
    ) -> list[Conversation]:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if session_id:
            query = query.where(Conversation.session_id == session_id)
        query = query.order_by(Conversation.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(reversed(result.scalars().all()))

    async def get_stale_sessions(self, older_than: datetime) -> list[str]:
        result = await self.session.execute(
            select(Conversation.session_id)
            .where(Conversation.created_at < older_than)
            .group_by(Conversation.session_id)
        )
        return list(result.scalars().all())

    async def get_session_messages(self, session_id: str) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_older_than(self, cutoff: datetime) -> int:
        result = await self.session.execute(
            delete(Conversation).where(Conversation.created_at < cutoff)
        )
        return result.rowcount or 0


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        memory_type: str,
        content: str,
        importance: float = 0.5,
        source: str = "extracted",
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> Memory:
        memory = Memory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            source=source,
            metadata_=metadata,
        )
        self.session.add(memory)
        await self.session.flush()
        if embedding:
            self.session.add(MemoryEmbedding(memory_id=memory.id, embedding=embedding))
            await self.session.flush()
        return memory

    async def get_goals(self, user_id: int) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.memory_type == MemoryType.GOAL)
            .order_by(Memory.importance.desc())
        )
        return list(result.scalars().all())

    async def get_reminders(self, user_id: int, limit: int = 5) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type.in_([MemoryType.GOAL, MemoryType.REMINDER]),
            )
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_relapse(self, user_id: int, days: int = 14) -> Memory | None:
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type == MemoryType.RELAPSE,
                Memory.created_at >= since,
            )
            .order_by(Memory.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_recent_setbacks(self, user_id: int, days: int = 30) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(func.count(Memory.id)).where(
                Memory.user_id == user_id,
                Memory.memory_type == MemoryType.RELAPSE,
                Memory.created_at >= since,
            )
        )
        return int(result.scalar_one())

    async def list_all(
        self, user_id: int, memory_type: str | None = None, search: str | None = None
    ) -> list[Memory]:
        query = select(Memory).where(Memory.user_id == user_id)
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        if search:
            query = query.where(Memory.content.ilike(f"%{search}%"))
        query = query.order_by(Memory.importance.desc(), Memory.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_type(self, user_id: int, memory_type: str | None = None) -> int:
        query = delete(Memory).where(Memory.user_id == user_id)
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        result = await self.session.execute(query)
        return result.rowcount or 0

    async def get_with_embeddings(self, user_id: int) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .options(selectinload(Memory.embedding))
            .where(Memory.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_recent_episodes(self, user_id: int, days: int = 30, limit: int = 5) -> list[Memory]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.memory_type == MemoryType.EPISODE,
                Memory.created_at >= since,
            )
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def get_top_memories(self, user_id: int, limit: int = 10) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.memory_type != MemoryType.EPISODE)
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def decay_importance(self, user_id: int, factor: float = 0.95) -> None:
        await self.session.execute(
            update(Memory)
            .where(Memory.user_id == user_id, Memory.importance > 0.1)
            .values(importance=Memory.importance * factor)
        )


class MealRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> Meal:
        meal = Meal(user_id=user_id, **data)
        self.session.add(meal)
        await self.session.flush()
        return meal

    async def get_recent(self, user_id: int, limit: int = 30) -> list[Meal]:
        result = await self.session.execute(
            select(Meal).where(Meal.user_id == user_id).order_by(Meal.logged_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def count_today(self, user_id: int) -> int:
        today = date.today()
        result = await self.session.execute(
            select(func.count(Meal.id)).where(
                Meal.user_id == user_id,
                func.date(Meal.logged_at) == today,
            )
        )
        return result.scalar_one()

    async def count_today_vision_calls(self, user_id: int, timezone: str = "Europe/Istanbul") -> int:
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Europe/Istanbul")

        now_local = datetime.now(tz)
        today = now_local.date()
        start = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        end = start + timedelta(days=1)

        result = await self.session.execute(
            select(func.count(Meal.id)).where(
                Meal.user_id == user_id,
                Meal.photo_path.isnot(None),
                Meal.logged_at >= start,
                Meal.logged_at < end,
            )
        )
        return result.scalar_one()

    async def get_today_stats(self, user_id: int, timezone: str = "Europe/Istanbul") -> dict[str, Any]:
        from zoneinfo import ZoneInfo

        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Europe/Istanbul")

        now_local = datetime.now(tz)
        today = now_local.date()
        start = datetime.combine(today, datetime.min.time()).replace(tzinfo=tz)
        end = start + timedelta(days=1)

        result = await self.session.execute(
            select(Meal)
            .where(
                Meal.user_id == user_id,
                Meal.logged_at >= start,
                Meal.logged_at < end,
            )
            .order_by(Meal.logged_at.asc())
        )
        meals = list(result.scalars().all())

        total_calories = sum(m.estimated_calories or 0 for m in meals)
        meal_summaries = []
        for m in meals:
            local_time = m.logged_at.astimezone(tz).strftime("%H:%M")
            cals = m.estimated_calories or "?"
            label = (m.ai_analysis or "Öğün")[:40]
            meal_summaries.append({"time": local_time, "calories": cals, "label": label})

        return {
            "count": len(meals),
            "total_calories": total_calories,
            "meals": meal_summaries,
            "local_time": now_local.strftime("%Y-%m-%d %H:%M"),
            "time_of_day": _time_of_day_label(now_local.hour),
        }


def _time_of_day_label(hour: int) -> str:
    if 5 <= hour < 11:
        return "sabah"
    if 11 <= hour < 15:
        return "öğle"
    if 15 <= hour < 21:
        return "akşam"
    return "gece"


class WorkoutRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> Workout:
        workout = Workout(user_id=user_id, **data)
        self.session.add(workout)
        await self.session.flush()
        return workout

    async def get_recent(self, user_id: int, days: int = 30) -> list[Workout]:
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(Workout)
            .where(Workout.user_id == user_id, Workout.logged_at >= since)
            .order_by(Workout.logged_at.desc())
        )
        return list(result.scalars().all())


class InsightRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> BehavioralInsight:
        insight = BehavioralInsight(user_id=user_id, **data)
        self.session.add(insight)
        await self.session.flush()
        return insight

    async def get_active(self, user_id: int, limit: int = 10) -> list[BehavioralInsight]:
        result = await self.session.execute(
            select(BehavioralInsight)
            .where(BehavioralInsight.user_id == user_id, BehavioralInsight.dismissed.is_(False))
            .order_by(BehavioralInsight.surfaced_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_recent(self, user_id: int, days: int = 7) -> int:
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(func.count(BehavioralInsight.id)).where(
                BehavioralInsight.user_id == user_id,
                BehavioralInsight.surfaced_at >= since,
            )
        )
        return result.scalar_one()

    async def dismiss(self, user_id: int, insight_id: int) -> bool:
        result = await self.session.execute(
            select(BehavioralInsight).where(
                BehavioralInsight.id == insight_id,
                BehavioralInsight.user_id == user_id,
            )
        )
        insight = result.scalar_one_or_none()
        if not insight:
            return False
        insight.dismissed = True
        return True

    async def dismiss_all_active(self, user_id: int) -> int:
        result = await self.session.execute(
            select(BehavioralInsight).where(
                BehavioralInsight.user_id == user_id,
                BehavioralInsight.dismissed.is_(False),
            )
        )
        insights = list(result.scalars().all())
        for insight in insights:
            insight.dismissed = True
        return len(insights)


class PersonalityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> PersonalityProfile | None:
        result = await self.session.execute(
            select(PersonalityProfile).where(PersonalityProfile.key == key)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[PersonalityProfile]:
        result = await self.session.execute(select(PersonalityProfile))
        return list(result.scalars().all())

    async def upsert(self, profile: PersonalityProfile) -> None:
        existing = await self.get(profile.key)
        if existing:
            existing.display_name = profile.display_name
            existing.system_prompt = profile.system_prompt
            existing.tone_rules = profile.tone_rules
        else:
            self.session.add(profile)
        await self.session.flush()


def new_session_id() -> str:
    return uuid4().hex
