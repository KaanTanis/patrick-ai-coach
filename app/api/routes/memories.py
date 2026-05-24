from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.repositories import MemoryRepository

router = APIRouter(prefix="/memories", tags=["memories"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_memories(
    type: str | None = Query(None, alias="type"),
    search: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select

    from app.models import User

    result = await session.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        return {"data": []}

    repo = MemoryRepository(session)
    memories = await repo.list_all(user.id, memory_type=type, search=search)

    return {
        "data": [
            {
                "id": m.id,
                "type": m.memory_type,
                "content": m.content,
                "importance": m.importance,
                "source": m.source,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ]
    }
