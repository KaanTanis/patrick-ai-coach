from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import CheckInRepository, MemoryRepository, UserRepository

router = Router()


@router.message(Command("ozet", "brief"))
async def cmd_briefing(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    checkins = CheckInRepository(session)
    memories = MemoryRepository(session)

    today = date.today()
    yesterday = today.fromordinal(today.toordinal() - 1)
    yesterday_ci = await checkins.get_by_date(user.id, yesterday)
    today_ci = await checkins.get_by_date(user.id, today)
    reminders = await memories.get_reminders(user.id, limit=3)

    lines = ["Günün özeti\n"]

    if yesterday_ci:
        lines.append(
            f"Dün: ruh hali {yesterday_ci.mood or '?'}/10, "
            f"stres {yesterday_ci.stress or '?'}/10, "
            f"enerji {yesterday_ci.energy or '?'}/10"
        )
    else:
        lines.append("Dün rapor yok.")

    if today_ci:
        lines.append(
            f"Bugün (şimdiye kadar): ruh hali {today_ci.mood or '?'}/10"
        )
    else:
        lines.append("Bugün henüz rapor yok — /rapor ile başlayabilirsin.")

    if reminders:
        lines.append("\nHatırlatmalar:")
        for r in reminders[:3]:
            lines.append(f"• {r.content[:100]}")

    episodes = await memories.get_recent_episodes(user.id, days=7, limit=3)
    weekly = next(
        (e for e in reversed(episodes) if (e.metadata_ or {}).get("type") == "weekly_reflection"),
        None,
    )
    if weekly:
        lines.append(f"\nHaftalık not: {weekly.content[:200]}...")

    lines.append("\nBugün için tek odak: küçük bir adım at.")
    await message.answer("\n".join(lines))
