from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analysis.deep_analyzer import DeepAnalyzer
from app.ai.openai_client import get_openai_client
from app.models import MemorySource, MemoryType
from app.repositories import MemoryRepository, UserRepository
from app.repositories.philosophy import DreamRepository, ShadowRepository
from app.services.lens import VALID_LENSES, set_lens
from app.services.preferences import PreferencesService

router = Router()


@router.message(Command("lens"))
async def cmd_lens(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip().lower() not in VALID_LENSES:
        await message.answer(
            "Kullanım: /lens jung | stoic | psych\n"
            "Sonraki mesajına bu perspektifle yanıt veririm."
        )
        return
    lens = parts[1].strip().lower()
    await set_lens(message.from_user.id, lens)
    labels = {"jung": "Jung", "stoic": "Stoacı", "psych": "Bilişsel"}
    await message.answer(f"{labels[lens]} lensi aktif — bir sonraki mesajına bu perspektifle bakacağım.")


@router.message(Command("ruya", "dream"))
async def cmd_dream(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Rüyanı anlat. Örnek: /ruya koridorda koşuyordum, su vardı...")
        return

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    content = parts[1].strip()

    prompt = f"""Jung perspektifinden rüya yorumu yap. Sembolik, kehanet değil, teşhis değil.
150 kelime altı Türkçe. Sonunda 1-2 yansıtıcı soru sor.

Rüya: {content}"""

    interpretation = await get_openai_client().chat(
        [{"role": "user", "content": prompt}], model="gpt-4o", max_tokens=400
    )

    dreams = DreamRepository(session)
    await dreams.create(
        user.id,
        {"content": content, "ai_interpretation": interpretation},
    )

    mem = MemoryRepository(session)
    embedding = await get_openai_client().embed(content[:200])
    await mem.create(
        user_id=user.id,
        memory_type=MemoryType.SYMBOL,
        content=f"Rüya: {content[:200]}",
        importance=0.7,
        source=MemorySource.MANUAL,
        metadata={"source": "dream"},
        embedding=embedding,
    )

    await message.answer(f"{interpretation}")


@router.message(Command("golge", "shadow"))
async def cmd_shadow(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Bugün hangi davranış seni rahatsız etti veya başkasında projekte ettin?\n"
            "Örnek: /golge patrona sinirlendim ama aslında kendi ertelemem..."
        )
        return

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    content = parts[1].strip()

    prompt = f"""Gölge perspektifinden kısa yansıtma yap.
"Bu gölge neyi koruyor olabilir?" formatında. Teşhis yok. 120 kelime altı Türkçe.

Not: {content}"""

    reflection = await get_openai_client().chat(
        [{"role": "user", "content": prompt}], model="gpt-4o", max_tokens=300
    )

    shadows = ShadowRepository(session)
    await shadows.create(user.id, content, reflection)
    await message.answer(reflection)


@router.message(Command("analiz", "analyze"))
async def cmd_analyze(message: Message, session: AsyncSession) -> None:
    parts = message.text.split()
    lens = "all"
    days = 7
    for p in parts[1:]:
        if p in {"jung", "stoic", "psych", "all"}:
            lens = p
        elif p.isdigit():
            days = min(int(p), 30)

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    analyzer = DeepAnalyzer(session)
    result = await analyzer.analyze(user.id, lens=lens, days=days)
    if result:
        await message.answer(result)


@router.message(Command("serbest", "free"))
async def cmd_free_mode(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    action = parts[1].strip().lower() if len(parts) > 1 else ""

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    prefs = PreferencesService(session)

    if action in {"ac", "aç", "on", "1"}:
        await prefs.update(user.id, {"free_mode": True, "proactive_nudges": False})
        await message.answer(
            "Serbest mod açık.\n"
            "- Daha uzun, keşif odaklı sohbet\n"
            "- Proaktif hatırlatmalar kapalı\n"
            "Kapatmak için: /serbest kapa"
        )
    elif action in {"kapa", "kapat", "off", "0"}:
        await prefs.update(user.id, {"free_mode": False, "proactive_nudges": True})
        await message.answer("Serbest mod kapalı. Normal moda döndün.")
    else:
        current = await prefs.is_free_mode(user.id)
        status = "açık" if current else "kapalı"
        await message.answer(
            f"Serbest mod: {status}\n"
            "Aç: /serbest ac\n"
            "Kapa: /serbest kapa"
        )
