import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.ranker import cosine_similarity, rank_memories
from app.ai.openai_client import get_openai_client
from app.models import Memory, MemoryType
from app.repositories import MemoryRepository

logger = structlog.get_logger()


class MemoryRetriever:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MemoryRepository(session)

    async def retrieve(self, user_id: int, query: str, intent: str = "free_chat") -> list[Memory]:
        goals = await self.repo.get_goals(user_id)
        all_memories = await self.repo.get_with_embeddings(user_id)

        if not query.strip():
            return goals[:5]

        query_embedding = await get_openai_client().embed(query)
        ranked = rank_memories(all_memories, query_embedding, intent)

        # Always include goals
        goal_ids = {g.id for g in goals}
        merged: list[Memory] = list(goals)
        for memory in ranked:
            if memory.id not in goal_ids:
                merged.append(memory)

        recent_relapse = await self.repo.get_recent_relapse(user_id)
        if recent_relapse and recent_relapse.id not in {m.id for m in merged}:
            merged.insert(0, recent_relapse)

        return merged[:15]

    async def find_similar(
        self, user_id: int, content: str, threshold: float = 0.92
    ) -> Memory | None:
        embedding = await get_openai_client().embed(content)
        memories = await self.repo.get_with_embeddings(user_id)
        for memory in memories:
            if memory.embedding is None:
                continue
            if cosine_similarity(embedding, memory.embedding.embedding) >= threshold:
                return memory
        return None
