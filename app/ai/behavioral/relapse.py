from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import get_openai_client
from app.ai.personalities.base import RELAPSE_GUARDRAILS
from app.models import MemoryType
from app.repositories import MemoryRepository, SmokingEventRepository


RELAPSE_KEYWORDS = {
    # Türkçe
    "sigara",
    "içtim",
    "içmiş",
    "relaps",
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
    # İngilizce (yedek)
    "smoked",
    "relapsed",
    "gave up",
    "binged",
    "failed",
    "slipped",
}


def detect_relapse_intent(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in RELAPSE_KEYWORDS)


class RelapseRecovery:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.memories = MemoryRepository(session)
        self.smoking = SmokingEventRepository(session)

    async def handle(self, user_id: int, message: str, personality_key: str = "companion") -> str:
        recent_relapse = await self.memories.get_recent_relapse(user_id, days=90)
        past_recovery = ""
        if recent_relapse:
            past_recovery = f"\nGeçmiş toparlanma notu: {recent_relapse.content}"

        await self.smoking.create(
            user_id,
            {
                "event_type": "relapse",
                "trigger_note": message[:500],
                "context": {"source": "chat"},
            },
        )

        await self.memories.create(
            user_id,
            memory_type=MemoryType.RELAPSE,
            content=message[:500],
            importance=0.85,
            source="extracted",
        )

        prompt = f"""Kullanıcı bir gerileme bildirdi. Toparlanma yanıtı oluştur.
{RELAPSE_GUARDRAILS}
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
