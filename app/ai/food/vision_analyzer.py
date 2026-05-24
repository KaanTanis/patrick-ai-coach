import structlog
from pathlib import Path

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context.bundle import ContextBuilder
from app.ai.food.formatter import format_food_response, parse_food_response
from app.ai.openai_client import get_openai_client
from app.config import get_settings
from app.repositories import MealRepository
from app.schemas.models import FoodAnalysisResult

logger = structlog.get_logger()
settings = get_settings()

FOOD_PROMPT = """Bu yemek fotoğrafını analiz et. Besin değerlerini tahmin et.
JSON formatında şu anahtarlarla dön (başka metin ekleme):
- estimated_calories (int)
- protein_g (float)
- carbs_g (float)
- fat_g (float)
- portion_description (string, Türkçe — yemeğin adı/kısa tanımı)
- confidence (low|medium|high)
- healthier_swap (pratik alternatif öneri, Türkçe)
- conversational_response (sıcak, pratik, 80 kelimenin altında Türkçe — veri dökümü değil)

Asla "bunu yememeliydin" deme. Bilgi ve seçim olarak çerçevele.

Kullanıcı bağlamı:
{context}
"""


class FoodVisionAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.meals = MealRepository(session)
        self.context = ContextBuilder(session)

    def _resize_image(self, source: Path, dest: Path, max_size: int = 1024) -> None:
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((max_size, max_size))
            img.save(dest, "JPEG", quality=85)

    def _build_context_prompt(self, bundle) -> str:
        parts = [
            f"Şu an: {bundle.local_time} ({bundle.user.timezone}) — {bundle.time_of_day}",
            f"Profil: {bundle.profile_summary[:400]}",
            bundle.today_meals_text,
        ]
        if bundle.episodic_summaries:
            parts.append("Geçmiş özetler:\n" + "\n".join(bundle.episodic_summaries[-3:]))
        if bundle.memories:
            parts.append(
                "İlgili hafızalar:\n"
                + "\n".join(f"- {m.content}" for m in bundle.memories[:5])
            )

        stats = bundle.today_meal_stats
        if stats["count"] >= settings.max_meals_before_nudge:
            parts.append(
                f"Not: Bugün zaten {stats['count']} öğün kayıtlı — "
                "gerekirse nazikçe 'bugün yeterli olabilir' diyebilirsin."
            )
        if stats["total_calories"] >= settings.daily_calorie_soft_limit:
            parts.append(
                f"Not: Bugünkü toplam kalori ~{stats['total_calories']} — "
                "hafif bir ton kullan."
            )
        return "\n".join(parts)

    async def _parse_with_fallback(self, raw: str) -> FoodAnalysisResult | None:
        result = parse_food_response(raw)
        if result:
            return result
        try:
            return await get_openai_client().chat_structured(
                [
                    {
                        "role": "system",
                        "content": "Metinden yemek analizi JSON'una dönüştür.",
                    },
                    {"role": "user", "content": raw},
                ],
                FoodAnalysisResult,
            )
        except Exception as exc:
            logger.warning("food.parse_fallback_failed", error=str(exc))
            return None

    async def analyze(self, user_id: int, photo_path: Path) -> str:
        bundle = await self.context.build(user_id, intent="food", include_meals=True)

        processed = photo_path.with_suffix(".jpg")
        self._resize_image(photo_path, processed)

        prompt = FOOD_PROMPT.format(context=self._build_context_prompt(bundle))
        raw = await get_openai_client().analyze_food_image(processed, prompt)

        result = await self._parse_with_fallback(raw)
        if not result:
            await self.meals.create(
                user_id,
                {"photo_path": str(processed), "ai_analysis": raw[:500]},
            )
            return "Yemeği analiz edemedim. Lütfen daha net bir fotoğraf gönder."

        stats = bundle.today_meal_stats
        projected_total = stats["total_calories"] + result.estimated_calories
        should_nudge = (
            stats["count"] + 1 >= settings.max_meals_before_nudge
            or projected_total >= settings.daily_calorie_soft_limit
        )

        formatted = format_food_response(
            result,
            local_time=bundle.local_time,
            time_of_day=bundle.time_of_day,
            meal_count=stats["count"],
            total_calories=stats["total_calories"],
            should_nudge_enough=should_nudge,
        )

        await self.meals.create(
            user_id,
            {
                "photo_path": str(processed),
                "estimated_calories": result.estimated_calories,
                "protein_g": result.protein_g,
                "carbs_g": result.carbs_g,
                "fat_g": result.fat_g,
                "ai_analysis": result.conversational_response or result.portion_description,
                "raw_vision": result.model_dump(),
            },
        )

        return formatted
