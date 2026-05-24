from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import yes_no_keyboard
from app.bot.states import ErasureStates
from app.repositories import UserRepository
from app.services.export import ErasureService

router = Router()


@router.message(Command("sil", "erase"))
async def cmd_erase_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ErasureStates.confirm)
    await message.answer(
        "Tüm verilerini kalıcı olarak silmek istediğine emin misin?\n"
        "Check-in, öğün, sohbet, hafıza ve fotoğraflar silinir. Geri alınamaz.",
        reply_markup=yes_no_keyboard("erase"),
    )


@router.callback_query(ErasureStates.confirm, F.data.startswith("erase:"))
async def cmd_erase_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await state.clear()

    if callback.data.split(":")[1] != "yes":
        await callback.message.edit_text("Silme işlemi iptal edildi.")
        return

    users = UserRepository(session)
    user = await users.get_or_create(callback.from_user.id, callback.from_user.full_name)
    erasure = ErasureService(session)
    counts = await erasure.erase_all(user.id, callback.from_user.id)

    summary = ", ".join(f"{k}={v}" for k, v in counts.items())
    await callback.message.edit_text(
        f"Tüm verilerin silindi.\n({summary})\n\n/basla ile yeniden başlayabilirsin."
    )
