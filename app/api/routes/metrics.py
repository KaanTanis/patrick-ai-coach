from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.repositories import CheckInRepository, InsightRepository, MealRepository, UserRepository

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(verify_api_key)])


@router.get("/weight")
async def get_weight_metrics(
    days: int = Query(90, ge=7, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    users = UserRepository(session)
    checkins = CheckInRepository(session)
    user_list = await _get_first_user(users)
    if not user_list:
        return {"data": []}

    user = user_list
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
    user = await _get_first_user(users)
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
    user = await _get_first_user(users)
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
    user = await _get_first_user(users)
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
    user = await _get_first_user(users)
    if not user:
        return {"checkins": [], "workouts": []}

    recent = await checkins.get_recent(user.id, days=days)
    return {
        "checkins": [str(c.date) for c in recent],
        "workouts": [str(c.date) for c in recent if c.workout_done],
    }


async def _get_first_user(users: UserRepository):
    from sqlalchemy import select

    from app.models import User

    result = await users.session.execute(select(User).limit(1))
    return result.scalar_one_or_none()
