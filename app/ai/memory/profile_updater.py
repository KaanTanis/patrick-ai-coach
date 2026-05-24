import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import get_openai_client
from app.repositories import ConversationRepository, MemoryRepository, UserRepository
from app.schemas.memory import ProfileUpdateResult

logger = structlog.get_logger()

PROFILE_PROMPT = """Kullanıcı profil özetini güncelle. Türkçe yaz.

Mevcut özet:
{current_summary}

Son konuşmalar:
{recent_messages}

İlgili hafızalar:
{memories}

Görev:
1. context_summary: 300-500 kelime, kullanıcıyı tanımlayan canlı profil (hedefler, vardiya, alışkanlıklar, tetikleyiciler, kişisel notlar)
2. schedule: vardiya saatleri, uyku penceresi, aktif saatler — bilinenleri koru, yenileriyle güncelle

Vardiya bilgisi yoksa schedule alanlarını null bırak."""


class ProfileUpdater:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.conversations = ConversationRepository(session)
        self.memories = MemoryRepository(session)

    async def update(self, user_id: int) -> None:
        user = await self.users.get_by_id(user_id)
        if not user:
            return

        recent = await self.conversations.get_recent(user_id, limit=10)
        if not recent:
            return

        memory_list = await self.memories.list_all(user_id)
        schedule_memories = [m for m in memory_list if m.memory_type == "schedule"][:5]
        top_memories = sorted(memory_list, key=lambda m: m.importance, reverse=True)[:8]

        memories_text = "\n".join(
            f"- [{m.memory_type}] {m.content}" for m in (schedule_memories + top_memories)
        )
        messages_text = "\n".join(f"{m.role}: {m.content}" for m in recent[-6:])

        prompt = PROFILE_PROMPT.format(
            current_summary=user.context_summary or "Henüz profil özeti yok.",
            recent_messages=messages_text,
            memories=memories_text or "Yok",
        )

        try:
            result = await get_openai_client().chat_structured(
                [
                    {"role": "system", "content": "Kullanıcı profilini yapılandırılmış JSON olarak güncelle."},
                    {"role": "user", "content": prompt},
                ],
                ProfileUpdateResult,
            )
        except Exception as exc:
            logger.error("profile.update_failed", user_id=user_id, error=str(exc))
            return

        schedule_dict = result.schedule.model_dump(exclude_none=True)
        await self.users.update_context(
            user_id,
            context_summary=result.context_summary,
            schedule=schedule_dict or user.schedule,
        )
        logger.info("profile.updated", user_id=user_id)
