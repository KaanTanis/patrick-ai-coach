import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.extractor import MemoryExtractor
from app.ai.openai_client import get_openai_client
from app.models import MemorySource, MemoryType
from app.repositories import ConversationRepository, MemoryRepository

logger = structlog.get_logger()


class SessionSummarizer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversations = ConversationRepository(session)
        self.memories = MemoryRepository(session)
        self.extractor = MemoryExtractor(session)

    async def summarize_session(self, session_id: str) -> str | None:
        messages = await self.conversations.get_session_messages(session_id)
        if len(messages) < 4:
            return None

        transcript = "\n".join(f"{m.role}: {m.content}" for m in messages)
        prompt = f"""Bu koçluk konuşmasını 2-3 cümlede özetle.
Duygusal durum, konuşulan davranışlar ve ortaya çıkan içgörülere odaklan.
Özeti Türkçe yaz.

{transcript}"""

        summary = await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=200,
        )

        if not summary.strip():
            return None

        user_id = messages[0].user_id
        embedding = await get_openai_client().embed(summary)
        await self.memories.create(
            user_id=user_id,
            memory_type=MemoryType.EPISODE,
            content=summary,
            importance=0.75,
            source=MemorySource.EXTRACTED,
            metadata={"session_id": session_id},
            embedding=embedding,
        )
        logger.info("session.summarized", session_id=session_id)
        return summary
