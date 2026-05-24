import structlog
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context.bundle import ContextBuilder
from app.ai.openai_client import get_openai_client
from app.config import get_settings
from app.infra.redis import get_redis
from app.repositories import CheckInRepository
from app.repositories.philosophy import (
    DreamRepository,
    EmotionRepository,
    ShadowRepository,
    StoicRitualRepository,
    ThoughtRepository,
)

logger = structlog.get_logger()
settings = get_settings()

LENS_PROMPTS = {
    "all": """Üç bölümlü derin analiz yaz (Türkçe):
## Jung Perspektifi
Sembolik temalar, gölge, tekrarlayan kalıplar. Teşhis yok.

## Stoacı Perspektif
Kontrol ikiligi, erdem pratiği, tutarlılık gözlemleri.

## Bilişsel Perspektif
Duygu-düşünce kalıpları, CBT açısından nazik gözlemler. Terapi değil.

Her bölüm 80-120 kelime. Somut verilere atıf yap.""",
    "jung": """Jung perspektifinden derin analiz yaz. Sembolik, arketipsel. Teşhis/kehanet yok. 150-200 kelime Türkçe.""",
    "stoic": """Stoacı perspektiften derin analiz yaz. Kontrol ikiligi, erdem, pratik. 150-200 kelime Türkçe.""",
    "psych": """CBT perspektifinden analiz yaz. Duygu-düşünce kalıpları. Terapi değil. 150-200 kelime Türkçe.""",
}


class DeepAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.context = ContextBuilder(session)
        self.check_ins = CheckInRepository(session)
        self.dreams = DreamRepository(session)
        self.shadows = ShadowRepository(session)
        self.thoughts = ThoughtRepository(session)
        self.stoic = StoicRitualRepository(session)
        self.emotions = EmotionRepository(session)

    async def _rate_limit_ok(self, user_id: int) -> bool:
        redis = await get_redis()
        key = f"analysis:daily:{user_id}:{datetime.now(timezone.utc).date()}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 86400)
        return count <= getattr(settings, "max_daily_analysis", 2)

    async def _gather_context(self, user_id: int, days: int) -> str:
        bundle = await self.context.build(user_id, intent="analysis")
        dreams = await self.dreams.get_recent(user_id, days=days, limit=10)
        shadows = await self.shadows.get_recent(user_id, days=days, limit=10)
        thoughts = await self.thoughts.get_recent(user_id, days=days, limit=10)
        rituals = await self.stoic.get_recent(user_id, days=days, limit=14)
        emotions = await self.emotions.get_recent(user_id, days=days, limit=20)
        checkins = await self.check_ins.get_recent(user_id, days=days)

        parts = [
            f"Profil: {bundle.profile_summary[:500]}",
            f"Check-in ({len(checkins)}): {bundle.checkin_snapshot[:400]}",
            f"Rüyalar: {[d.content[:80] for d in dreams]}",
            f"Gölge notları: {[s.content[:80] for s in shadows]}",
            f"Düşünce kayıtları: {len(thoughts)} adet",
            f"Stoic ritüeller: {len(rituals)} adet",
            f"Duygu check-in: {[(e.emotion, e.intensity) for e in emotions[:5]]}",
        ]
        return "\n".join(parts)

    async def analyze(
        self, user_id: int, lens: str = "all", days: int = 7
    ) -> str | None:
        if not await self._rate_limit_ok(user_id):
            return "Bugünkü analiz limitine ulaştın. Yarın tekrar deneyebilirsin."

        context = await self._gather_context(user_id, days)
        prompt_key = lens if lens in LENS_PROMPTS else "all"
        prompt = f"""{LENS_PROMPTS[prompt_key]}

Son {days} gün verileri:
{context}
"""

        return await get_openai_client().chat(
            [{"role": "user", "content": prompt}],
            model="gpt-4o",
            max_tokens=900,
        )
