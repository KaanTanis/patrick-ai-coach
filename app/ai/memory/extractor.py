import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.retriever import MemoryRetriever
from app.ai.openai_client import get_openai_client
from app.models import MemoryType
from app.repositories import MemoryRepository
from app.schemas.memory import MemoryExtracted

logger = structlog.get_logger()

EXTRACTION_PROMPT = """Bu konuşma alışverişini analiz et ve kullanıcı hakkında kalıcı hafızalar çıkar.
Sadece haftalar/aylar boyunca kişisel koça yardımcı olacak bilgileri çıkar.
Türler: fact, trigger, pattern, goal, relapse, schedule, episode
schedule: vardiya saatleri, uyku penceresi, iş programı, aktif saatler
episode: önemli bir olay/dönem özeti (nadir, yüksek değerli)
Kalıcı bir şey yoksa boş liste dön.
Hafıza içeriklerini Türkçe yaz.

Kullanıcı mesajı: {user_message}
Asistan yanıtı: {assistant_response}
"""


class MemoryExtractor:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MemoryRepository(session)
        self.retriever = MemoryRetriever(session)

    async def extract_and_store(
        self, user_id: int, user_message: str, assistant_response: str
    ) -> list[str]:
        messages = [
            {"role": "system", "content": "Kalıcı kişisel hafızaları yapılandırılmış JSON olarak çıkar."},
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(
                    user_message=user_message,
                    assistant_response=assistant_response,
                ),
            },
        ]
        try:
            result = await get_openai_client().chat_structured(messages, MemoryExtracted)
        except Exception as exc:
            logger.error("memory.extract_failed", error=str(exc))
            return []

        stored: list[str] = []
        for item in result.memories:
            content = item.content.strip()
            memory_type = item.memory_type
            importance = item.importance

            if not content:
                continue

            if memory_type == MemoryType.RELAPSE or memory_type == MemoryType.TRIGGER:
                importance = max(importance, 0.7)
            if memory_type == MemoryType.SCHEDULE:
                importance = max(importance, 0.85)
            if memory_type == MemoryType.EPISODE:
                importance = max(importance, 0.75)

            similar = await self.retriever.find_similar(user_id, content)
            if similar:
                similar.content = content
                similar.importance = max(similar.importance, importance)
                stored.append(f"updated:{content[:50]}")
                continue

            embedding = await get_openai_client().embed(content)
            await self.repo.create(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                importance=importance,
                embedding=embedding,
            )
            stored.append(f"created:{content[:50]}")

        return stored
