from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_api_key
from app.api.user_lookup import get_primary_user
from app.repositories import MemoryRepository, UserRepository

router = APIRouter(prefix="/memories", tags=["memories"], dependencies=[Depends(verify_api_key)])


@router.get("")
async def list_memories(
    type: str | None = Query(None, alias="type"),
    search: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    user = await get_primary_user(session, UserRepository(session))
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
