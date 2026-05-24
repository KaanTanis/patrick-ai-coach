from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import InsightRepository, UserRepository
from app.services.export import ExportService, ForgetService

router = Router()


def _insight_keyboard(insights: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"Gizle: {i.title[:30]}", callback_data=f"insight:dismiss:{i.id}")]
        for i in insights[:5]
    ]
    if insights:
        buttons.append([InlineKeyboardButton(text="Tümünü gizle", callback_data="insight:dismiss:all")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("durum", "insights"))
async def cmd_insights(message: Message, session: AsyncSession) -> None:
    parts = message.text.split(maxsplit=1)
    sub = parts[1].strip().lower() if len(parts) > 1 else ""

    users = UserRepository(session)
    insights_repo = InsightRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    if sub.startswith("gizle"):
        tokens = sub.split()
        if len(tokens) >= 2 and tokens[1].isdigit():
            ok = await insights_repo.dismiss(user.id, int(tokens[1]))
            await message.answer("İçgörü gizlendi." if ok else "İçgörü bulunamadı.")
            return
        count = await insights_repo.dismiss_all_active(user.id)
        await message.answer(f"{count} içgörü gizlendi.")
        return

    insights = await insights_repo.get_active(user.id, limit=5)
    if not insights:
        await message.answer(
            "Henüz içgörü yok. Her gün check-in yap — kalıplar zamanla ortaya çıkar."
        )
        return

    lines = ["Son içgörüler:\n"]
    for i, insight in enumerate(insights, 1):
        action = ""
        if insight.evidence and insight.evidence.get("action_suggestion"):
            action = f"\n→ {insight.evidence['action_suggestion']}"
        lines.append(f"{i}. **{insight.title}**\n{insight.body}{action}\n")
    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=_insight_keyboard(insights),
    )


@router.callback_query(F.data.startswith("insight:dismiss:"))
async def dismiss_insight_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(callback.from_user.id, callback.from_user.full_name)
    repo = InsightRepository(session)
    target = callback.data.split(":")[-1]

    if target == "all":
        count = await repo.dismiss_all_active(user.id)
        await callback.answer(f"{count} içgörü gizlendi")
    else:
        ok = await repo.dismiss(user.id, int(target))
        await callback.answer("Gizlendi" if ok else "Bulunamadı")

    await callback.message.edit_reply_markup(reply_markup=None)


@router.message(Command("veriler", "export"))
async def cmd_export(message: Message, session: AsyncSession) -> None:
    from aiogram.types import BufferedInputFile

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
