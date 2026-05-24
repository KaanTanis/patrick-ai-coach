from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.api.user_lookup import get_primary_user
from app.repositories import MemoryRepository, UserRepository
from app.services.timeline import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def get_timeline(
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"data": []}

    service = TimelineService(session)
    return {"data": await service.build(user.id, days=days)}


@router.get("/weekly-summary")
async def get_weekly_summary(session: AsyncSession = Depends(get_db_session)):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"summary": None}

    service = TimelineService(session)
    return {"summary": await service.get_weekly_summary(user.id)}


@router.get("/correlations")
async def get_correlations(session: AsyncSession = Depends(get_db_session)):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"data": []}

    service = TimelineService(session)
    flags = await service.get_correlation_flags(user.id)
    return {"data": flags}


@router.get("/goals")
async def get_goals(session: AsyncSession = Depends(get_db_session)):
    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"data": []}

    memories = MemoryRepository(session)
    reminders = await memories.get_reminders(user.id, limit=20)
    return {
        "data": [
            {
                "type": m.memory_type,
                "content": m.content,
                "importance": m.importance,
                "metadata": m.metadata_ or {},
                "updated_at": m.updated_at.isoformat(),
            }
            for m in reminders
        ]
    }
