from sqlalchemy.ext.asyncio import AsyncSession

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


# Backward-compatible aliases
detect_relapse_intent = detect_setback_intent


class SetbackRecovery:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memories = MemoryRepository(session)

    async def handle(self, user_id: int, message: str, personality_key: str = "companion") -> str:
        recent = await self.memories.get_recent_relapse(user_id, days=90)
        past_recovery = ""
        if recent:
            past_recovery = f"\nGeçmiş toparlanma notu: {recent.content}"

        await self.memories.create(
            user_id,
            memory_type=MemoryType.RELAPSE,
            content=message[:500],
            importance=0.85,
            source=MemorySource.EXTRACTED,
        )

        prompt = f"""Kullanıcı zor bir an veya gerileme bildirdi. Toparlanma yanıtı oluştur.
{SETBACK_GUARDRAILS}
{past_recovery}

Kullanıcı mesajı: {message}
"""
        if personality_key.startswith("stoic"):
            prompt += """
Stoacı perspektif ekle: amor fati, kontrol ikiligi, eğitim olarak çerçevele.
Marcus/Epiktetos tonunda kısa bir aforizma ekle."""
        prompt += """
Yapı: kabul et → normalleştir → kimliği ayır → bir mikro adım → isteğe bağlı nazik soru.
150 kelimenin altında tut. Türkçe yaz."""

        return await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o",
            max_tokens=300,
        )


RelapseRecovery = SetbackRecovery
