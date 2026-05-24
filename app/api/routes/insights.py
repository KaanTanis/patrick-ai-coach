from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.api.user_lookup import get_primary_user
from app.repositories import InsightRepository, UserRepository

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_insights(
    include_dismissed: bool = False,
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select

    from app.models import BehavioralInsight

    user = await get_primary_user(session, UserRepository(session))
    if not user:
        return {"data": []}

    repo = InsightRepository(session)
    if include_dismissed:
        res = await session.execute(
            select(BehavioralInsight)
            .where(BehavioralInsight.user_id == user.id)
            .order_by(BehavioralInsight.surfaced_at.desc())
            .limit(50)
        )
        insights = list(res.scalars().all())
    else:
        insights = await repo.get_active(user.id, limit=50)

    return {
        "data": [
            {
                "id": i.id,
                "type": i.insight_type,
                "title": i.title,
                "body": i.body,
                "confidence": i.confidence,
                "evidence": i.evidence,
                "surfaced_at": i.surfaced_at.isoformat(),
                "dismissed": i.dismissed,
            }
            for i in insights
        ]
    }
