from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.api.user_lookup import get_primary_user
from app.repositories import CheckInRepository, MealRepository, UserRepository

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(verify_api_key)])


@router.get("/weight")
async def get_weight_metrics(
    days: int = Query(90, ge=7, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    users = UserRepository(session)
    checkins = CheckInRepository(session)
    user = await get_primary_user(session, users)
    if not user:
        return {"data": []}

    recent = await checkins.get_recent(user.id, days=days)
    return {
        "data": [
            {"date": str(c.date), "weight": float(c.weight) if c.weight else None}
            for c in sorted(recent, key=lambda x: x.date)
            if c.weight is not None
        ]
    }


@router.get("/checkins")
async def get_checkin_metrics(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    users = UserRepository(session)
    checkins = CheckInRepository(session)
    user = await get_primary_user(session, users)
    if not user:
        return {"data": []}

    recent = await checkins.get_recent(user.id, days=days)
    return {
        "data": [
            {
                "date": str(c.date),
                "mood": c.mood,
                "sleep_quality": c.sleep_quality,
                "energy": c.energy,
                "smoking_craving": c.smoking_craving,
                "stress": c.stress,
                "motivation": c.motivation,
                "workout_done": c.workout_done,
            }
            for c in sorted(recent, key=lambda x: x.date)
        ]
    }


@router.get("/calories")
async def get_calorie_metrics(
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_db_session),
):
    users = UserRepository(session)
    meals_repo = MealRepository(session)
    user = await get_primary_user(session, users)
    if not user:
        return {"data": []}

    meals = await meals_repo.get_recent(user.id, limit=200)
    cutoff = date.today() - timedelta(days=days)
    daily: dict[str, int] = {}
    for meal in meals:
        d = meal.logged_at.date()
        if d < cutoff or not meal.estimated_calories:
            continue
        key = str(d)
        daily[key] = daily.get(key, 0) + meal.estimated_calories

    return {"data": [{"date": k, "calories": v} for k, v in sorted(daily.items())]}


@router.get("/smoking")
async def get_smoking_metrics(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    from app.repositories import SmokingEventRepository

    users = UserRepository(session)
    smoking = SmokingEventRepository(session)
    checkins = CheckInRepository(session)
    user = await get_primary_user(session, users)
    if not user:
        return {"data": []}

    recent_checkins = await checkins.get_recent(user.id, days=days)
    events = await smoking.get_recent(user.id, days=days)

    return {
        "cravings": [
            {"date": str(c.date), "level": c.smoking_craving}
            for c in sorted(recent_checkins, key=lambda x: x.date)
            if c.smoking_craving is not None
        ],
        "events": [
            {
                "type": e.event_type,
                "intensity": e.intensity,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
    }


@router.get("/consistency/heatmap")
async def get_consistency_heatmap(
    days: int = Query(90, ge=7, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    users = UserRepository(session)
    checkins = CheckInRepository(session)
    user = await get_primary_user(session, users)
    if not user:
        return {"checkins": [], "workouts": []}

    recent = await checkins.get_recent(user.id, days=days)
    return {
        "checkins": [str(c.date) for c in recent],
        "workouts": [str(c.date) for c in recent if c.workout_done],
    }


@router.get("/tokens")
async def get_token_usage(
    days: int = Query(7, ge=1, le=30),
    session: AsyncSession = Depends(get_db_session),
):
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, select

    from app.models import Conversation

    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"total_tokens": 0, "estimated_cost_usd": 0.0}

    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await session.execute(
        select(func.coalesce(func.sum(Conversation.token_count), 0)).where(
            Conversation.user_id == user.id,
            Conversation.role == "assistant",
            Conversation.created_at >= since,
        )
    )
    total = int(result.scalar_one())
    estimated_cost = round(total * 0.000005, 4)
    return {"total_tokens": total, "estimated_cost_usd": estimated_cost, "days": days}
