from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.api.user_lookup import get_primary_user
from app.repositories import UserRepository
from app.repositories.philosophy import (
    DreamRepository,
    EmotionRepository,
    StoicRitualRepository,
)

router = APIRouter(prefix="/philosophy", tags=["philosophy"], dependencies=[Depends(verify_api_key)])


@router.get("/emotions")
async def get_emotion_series(
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"data": []}

    repo = EmotionRepository(session)
    entries = await repo.get_recent(user.id, days=days, limit=100)
    return {
        "data": [
            {
                "emotion": e.emotion,
                "intensity": e.intensity,
                "logged_at": e.logged_at.isoformat(),
            }
            for e in sorted(entries, key=lambda x: x.logged_at)
        ]
    }


@router.get("/stoic/streak")
async def get_stoic_streak(
    days: int = Query(30, ge=7, le=90),
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"morning": 0, "evening": 0, "total": 0}

    repo = StoicRitualRepository(session)
    counts = await repo.count_recent_by_type(user.id, days=days)
    morning = counts.get("morning", 0)
    evening = counts.get("evening", 0)
    return {"morning": morning, "evening": evening, "total": morning + evening, "days": days}


@router.get("/themes")
async def get_monthly_themes(
    days: int = Query(30, ge=7, le=90),
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"words": []}

    dreams = DreamRepository(session)
    entries = await dreams.get_recent(user.id, days=days, limit=50)
    words: Counter[str] = Counter()
    stop = {"ve", "bir", "için", "ile", "de", "da", "the", "a", "an", "in", "on", "ben", "çok", "gibi"}
    for entry in entries:
        for word in entry.content.lower().split():
            cleaned = word.strip(".,!?;:\"'()[]")
            if len(cleaned) > 3 and cleaned not in stop:
                words[cleaned] += 1

    return {"words": [{"word": w, "count": c} for w, c in words.most_common(15)]}
