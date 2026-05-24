from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DreamEntry,
    EmotionCheckin,
    ShadowNote,
    StoicRitual,
    ThoughtRecord,
)


class DreamRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> DreamEntry:
        entry = DreamEntry(user_id=user_id, **data)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_recent(self, user_id: int, days: int = 30, limit: int = 20) -> list[DreamEntry]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(DreamEntry)
            .where(DreamEntry.user_id == user_id, DreamEntry.logged_at >= since)
            .order_by(DreamEntry.logged_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ShadowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, content: str, ai_reflection: str | None = None) -> ShadowNote:
        note = ShadowNote(user_id=user_id, content=content, ai_reflection=ai_reflection)
        self.session.add(note)
        await self.session.flush()
        return note

    async def get_recent(self, user_id: int, days: int = 30, limit: int = 20) -> list[ShadowNote]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(ShadowNote)
            .where(ShadowNote.user_id == user_id, ShadowNote.logged_at >= since)
            .order_by(ShadowNote.logged_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ThoughtRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> ThoughtRecord:
        record = ThoughtRecord(user_id=user_id, **data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_recent(self, user_id: int, days: int = 30, limit: int = 20) -> list[ThoughtRecord]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(ThoughtRecord)
            .where(ThoughtRecord.user_id == user_id, ThoughtRecord.logged_at >= since)
            .order_by(ThoughtRecord.logged_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class StoicRitualRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> StoicRitual:
        ritual = StoicRitual(user_id=user_id, **data)
        self.session.add(ritual)
        await self.session.flush()
        return ritual

    async def get_recent(
        self, user_id: int, ritual_type: str | None = None, days: int = 30, limit: int = 30
    ) -> list[StoicRitual]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = select(StoicRitual).where(
            StoicRitual.user_id == user_id, StoicRitual.logged_at >= since
        )
        if ritual_type:
            query = query.where(StoicRitual.ritual_type == ritual_type)
        query = query.order_by(StoicRitual.logged_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_recent_by_type(self, user_id: int, days: int = 7) -> dict[str, int]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(StoicRitual.ritual_type, func.count(StoicRitual.id))
            .where(StoicRitual.user_id == user_id, StoicRitual.logged_at >= since)
            .group_by(StoicRitual.ritual_type)
        )
        return {row[0]: row[1] for row in result.all()}


class EmotionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, data: dict[str, Any]) -> EmotionCheckin:
        entry = EmotionCheckin(user_id=user_id, **data)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_recent(self, user_id: int, days: int = 30, limit: int = 50) -> list[EmotionCheckin]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            select(EmotionCheckin)
            .where(EmotionCheckin.user_id == user_id, EmotionCheckin.logged_at >= since)
            .order_by(EmotionCheckin.logged_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
