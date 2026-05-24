from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.model_settings import chat_model
from app.ai.openai_client import get_openai_client
from app.ai.personalities.base import SETBACK_GUARDRAILS
from app.models import MemorySource, MemoryType
from app.repositories import MemoryRepository


SETBACK_KEYWORDS = {
    "geriledim",
    "gerileme",
    "pes ettim",
    "vazgeçtim",
    "abur",
    "aştım",
    "aşırı yedim",
    "binge",
    "kayboldum",
    "tökezledim",
    "başarısız",
    "antrenmanı kaçırdım",
    "spora gitmedim",
    "bozuldu",
    "yapamadım",
    "relaps",
    "relapsed",
    "gave up",
    "binged",
    "failed",
    "slipped",
}


def detect_setback_intent(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in SETBACK_KEYWORDS)


detect_relapse_intent = detect_setback_intent


class SetbackRecovery:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memories = MemoryRepository(session)

    async def handle(self, user_id: int, message: str, personality_key: str = "companion") -> str:
        return await self.complete_flow(
            user_id=user_id,
            description=message,
            trigger=None,
            micro_action=None,
            personality_key=personality_key,
        )

    async def complete_flow(
        self,
        user_id: int,
        description: str,
        trigger: str | None,
        micro_action: str | None,
        personality_key: str = "companion",
        telegram_id: int | None = None,
    ) -> str:
        recent = await self.memories.get_recent_relapse(user_id, days=90)
        past_recovery = ""
        if recent:
            past_recovery = f"\nGeçmiş toparlanma notu: {recent.content}"

        content_parts = [description]
        if trigger:
            content_parts.append(f"Tetikleyici: {trigger}")
        if micro_action:
            content_parts.append(f"Mikro adım: {micro_action}")

        await self.memories.create(
            user_id,
            memory_type=MemoryType.RELAPSE,
            content=" | ".join(content_parts)[:500],
            importance=0.85,
            source=MemorySource.EXTRACTED,
            metadata={"trigger": trigger, "micro_action": micro_action},
        )

        if micro_action:
            await self.memories.create(
                user_id,
                memory_type=MemoryType.REMINDER,
                content=f"Gerileme sonrası adım: {micro_action}",
                importance=0.75,
                source=MemorySource.MANUAL,
                metadata={"type": "setback_action"},
            )

        prompt = f"""Kullanıcı zor bir an veya gerileme bildirdi. Toparlanma yanıtı oluştur.
{SETBACK_GUARDRAILS}
{past_recovery}

Açıklama: {description}
Tetikleyici: {trigger or 'belirtilmedi'}
Önerilen mikro adım: {micro_action or 'henüz yok'}
"""
        if personality_key.startswith("stoic"):
            prompt += """
Stoacı perspektif ekle: amor fati, kontrol ikiligi, eğitim olarak çerçevele.
Marcus/Epiktetos tonunda kısa bir aforizma ekle."""
        prompt += """
Yapı: kabul et → normalleştir → kimliği ayır → mikro adımı onayla → isteğe bağlı nazik soru.
150 kelimenin altında tut. Türkçe yaz."""

        response = await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model=chat_model(),
            max_tokens=300,
        )

        if telegram_id:
            from app.infra.redis import enqueue_job

            await enqueue_job(
                "setback_followup_task",
                user_id,
                telegram_id,
                _defer_by=timedelta(hours=36),
            )

        return response


RelapseRecovery = SetbackRecovery
