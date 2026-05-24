from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.checkin import save_partial_checkin
from app.repositories import UserRepository
from app.services.preferences import PreferencesService

router = Router()


@router.message(Command("iptal"))
@router.message(F.text.lower().in_({"iptal", "vazgeç", "vazgec"}))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("İptal edilecek aktif bir işlem yok.")
        return

    if current and current.startswith("OnboardingStates:"):
        await state.clear()
        users = UserRepository(session)
        user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
        prefs = PreferencesService(session)
        await prefs.update(user.id, {"onboarding_complete": True})
        await message.answer("Kurulum atlandı. İstediğin zaman /basla ile devam edebilirsin.")
        return

    if await save_partial_checkin(message, state, session):
        return

    await state.clear()
    await message.answer("Tamam, sohbete döndük. Ne hakkında konuşmak istersin?")
