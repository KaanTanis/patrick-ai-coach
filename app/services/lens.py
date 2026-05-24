from app.config import get_settings
from app.infra.redis import get_redis

settings = get_settings()

LENS_KEY_PREFIX = "lens:"
VALID_LENSES = {"jung", "stoic", "psych"}

LENS_PROMPTS = {
    "jung": """Geçici lens: Jung perspektifi.
Sembolik ve arketipsel çerçevele. Gölge, persona, tekrarlayan temalar.
Teşhis koyma. Kehanet etme. Derin ama kısa sorular sor.""",
    "stoic": """Geçici lens: Stoacı perspektif.
Kontrol edebildiklerin / edemediklerin ayrımı. Erdem ve pratik odak.
Kısa, net, felsefi ama sıcak. Duyguları bastırma — çerçevele.""",
    "psych": """Geçici lens: CBT / bilişsel rehber perspektifi.
Duygu adlandırma, otomatik düşünce, kanıt sorgulama.
Gerçek terapi değil — koçluk aracı. Teşhis ve ilaç önerme.""",
}


async def set_lens(telegram_id: int, lens: str) -> None:
    if lens not in VALID_LENSES:
        raise ValueError(f"Invalid lens: {lens}")
    redis = await get_redis()
    await redis.setex(
        f"{LENS_KEY_PREFIX}{telegram_id}",
        settings.chat_session_ttl_minutes * 60,
        lens,
    )


async def get_lens(telegram_id: int) -> str | None:
    redis = await get_redis()
    value = await redis.get(f"{LENS_KEY_PREFIX}{telegram_id}")
    return value if value in VALID_LENSES else None


async def clear_lens(telegram_id: int) -> None:
    redis = await get_redis()
    await redis.delete(f"{LENS_KEY_PREFIX}{telegram_id}")


def lens_prompt(lens: str | None) -> str:
    if not lens:
        return ""
    return LENS_PROMPTS.get(lens, "")
