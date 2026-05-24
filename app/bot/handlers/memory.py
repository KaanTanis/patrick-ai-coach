from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MemoryType
from app.repositories import MemoryRepository, UserRepository

router = Router()

MEMORY_TYPE_TR = {
    "fact": "Bilgi",
    "trigger": "Tetikleyici",
    "pattern": "Kalıp",
    "goal": "Hedef",
    "reminder": "Hatırlatma",
    "insight": "İçgörü",
    "relapse": "Gerileme",
    "schedule": "Program",
    "episode": "Olay özeti",
}


@router.message(Command("hatirla", "remember"))
async def cmd_remember(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    memories = MemoryRepository(session)
    top = await memories.get_top_memories(user.id, limit=10)
    episodes = await memories.get_recent_episodes(user.id, days=30, limit=5)
    reminders = await memories.get_reminders(user.id, limit=5)

    parts = ["Seni nasıl tanıyorum\n"]

    if user.context_summary:
        parts.append("--- Profil ---")
        parts.append(user.context_summary[:800])
        if len(user.context_summary) > 800:
            parts.append("...")
    else:
        parts.append("--- Profil ---")
        parts.append("Henüz profil özeti oluşturulmadı.")

    if reminders:
        parts.append("\n--- Hatırlatmalar / hedefler ---")
        for r in reminders:
            meta = r.metadata_ or {}
            extra = []
            if meta.get("deadline"):
                extra.append(f"son: {meta['deadline']}")
            if meta.get("frequency"):
                extra.append(meta["frequency"])
            suffix = f" ({', '.join(extra)})" if extra else ""
            parts.append(f"• {r.content[:120]}{suffix}")

    progress = await memories.get_recent_episodes(user.id, days=14, limit=5)
    goal_updates = [
        e for e in progress if (e.metadata_ or {}).get("type") == "goal_progress"
    ]
    if goal_updates:
        parts.append("\n--- Hedef ilerlemesi ---")
        for ep in goal_updates[:3]:
            parts.append(f"• {ep.content[:150]}")

    if user.schedule:
        parts.append("\n--- Program / vardiya ---")
        for key, value in user.schedule.items():
            if value:
                parts.append(f"• {key}: {value}")

    if episodes:
        parts.append("\n--- Son olay özetleri ---")
        for ep in episodes:
            date_str = ep.created_at.strftime("%d.%m.%Y")
            parts.append(f"• [{date_str}] {ep.content[:120]}")

    if top:
        parts.append("\n--- Önemli hafıza kayıtları ---")
        for m in top[:10]:
            if m.memory_type in {MemoryType.GOAL, MemoryType.REMINDER}:
                continue
            label = MEMORY_TYPE_TR.get(m.memory_type, m.memory_type)
            parts.append(f"• [{label}] {m.content[:100]}")

    if not top and not episodes and not user.context_summary and not reminders:
        parts.append("\nHenüz kayıtlı hafıza yok. Sohbet ettikçe seni tanımaya başlayacağım.")

    text = "\n".join(parts)
    if len(text) > 4000:
        text = text[:3990] + "\n..."
    await message.answer(text)
