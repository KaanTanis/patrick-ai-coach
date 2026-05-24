from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import PersonalityRepository, UserRepository

router = Router()

PERSONALITY_KEYS = ["stoic", "therapist", "coach", "jungian", "companion"]


@router.message(Command("mod", "personality"))
async def cmd_personality(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    users = UserRepository(session)
    personalities = PersonalityRepository(session)

    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    if len(parts) < 2:
        all_profiles = await personalities.list_all()
        lines = ["Mevcut kişilik modları:"]
        for p in all_profiles:
            marker = " (aktif)" if p.key == user.personality_key else ""
            lines.append(f"• {p.key} — {p.display_name}{marker}")
        lines.append("\nKullanım: /mod stoic")
        await message.answer("\n".join(lines))
        return

    key = parts[1].strip().lower()
    if key not in PERSONALITY_KEYS:
        await message.answer(f"Bilinmeyen mod. Seçenekler: {', '.join(PERSONALITY_KEYS)}")
        return

    profile = await personalities.get(key)
    if not profile:
        await message.answer("Kişilik modu veritabanında bulunamadı. Önce seed script çalıştır.")
        return

    await users.update_personality(user.id, key)
    await message.answer(
        f"**{profile.display_name}** moduna geçildi.", parse_mode="Markdown"
    )
