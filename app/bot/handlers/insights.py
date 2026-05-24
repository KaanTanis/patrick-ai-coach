from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import InsightRepository, UserRepository
from app.services.export import ExportService, ForgetService

router = Router()


@router.message(Command("durum", "insights"))
async def cmd_insights(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    insights_repo = InsightRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    insights = await insights_repo.get_active(user.id, limit=5)
    if not insights:
        await message.answer(
            "Henüz içgörü yok. Her gün check-in yap — kalıplar zamanla ortaya çıkar."
        )
        return

    lines = ["Son içgörüler:\n"]
    for i, insight in enumerate(insights, 1):
        lines.append(f"{i}. **{insight.title}**\n{insight.body}\n")
    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("veriler", "export"))
async def cmd_export(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    export = ExportService(session)
    data = await export.export_json(user.id)
    file = BufferedInputFile(data.encode(), filename="tbot_export.json")
    await message.answer_document(file, caption="Tüm verilerinin dışa aktarımı.")


@router.message(Command("unut", "forget"))
async def cmd_forget(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    memory_type = parts[1].strip().lower() if len(parts) > 1 else None

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    forget = ForgetService(session)

    count = await forget.forget_memories(user.id, memory_type)
    suffix = f" ('{memory_type}' türünde)" if memory_type else ""
    await message.answer(f"{count} hafıza kaydı silindi{suffix}.")
