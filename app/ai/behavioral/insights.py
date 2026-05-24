import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.analyzer import BehavioralAnalyzer
from app.ai.openai_client import get_openai_client
from app.repositories import InsightRepository

logger = structlog.get_logger()

FLAG_PROMPTS = {
    "stress_smoking_correlation": "Yüksek stresli günlerde sigara isteği artıyor.",
    "sleep_motivation_link": "Kötü uyku kalitesinden sonra motivasyon düşüyor.",
    "workout_inconsistency": "Son dönemde antrenman tutarlılığı düşük.",
    "recurring_relapse": "Son 30 günde birden fazla sigara relapsi tespit edildi.",
    "stress_eating_pattern": "Yüksek stresli günlerde kalori alımı artıyor.",
}


class InsightGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.analyzer = BehavioralAnalyzer(session)
        self.insights = InsightRepository(session)

    async def generate(self, user_id: int) -> list[str]:
        recent_count = await self.insights.count_recent(user_id, days=7)
        if recent_count >= 2:
            return []

        flags = await self.analyzer.detect_patterns(user_id)
        if not flags:
            return []

        created: list[str] = []
        for flag in flags[:2]:
            flag_name = flag["flag"]
            evidence = flag["evidence"]
            seed = FLAG_PROMPTS.get(flag_name, flag_name)

            prompt = f"""Kişisel koçluk uygulaması için bir davranış içgörüsü oluştur.
Tespit edilen kalıp: {seed}
Kanıt: {json.dumps(evidence)}
JSON anahtarları: title (kısa, Türkçe), body (2-3 cümle, sıcak, Türkçe), insight_type (correlation|trend|warning|celebration), confidence (0-1)."""

            response = await get_openai_client().chat(
                [{"role": "user", "content": prompt}],
                model="gpt-4o",
                max_tokens=300,
            )

            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                data = {
                    "title": seed,
                    "body": response,
                    "insight_type": "correlation",
                    "confidence": 0.7,
                }

            confidence = float(data.get("confidence", 0.7))
            if confidence < 0.65:
                continue

            await self.insights.create(
                user_id,
                {
                    "insight_type": data.get("insight_type", "correlation"),
                    "title": data.get("title", seed),
                    "body": data.get("body", response),
                    "evidence": evidence,
                    "confidence": confidence,
                },
            )
            created.append(data.get("title", seed))

        return created
