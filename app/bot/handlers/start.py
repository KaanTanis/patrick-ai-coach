from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.onboarding import needs_onboarding, start_onboarding
from app.bot.keyboards import main_menu_keyboard
from app.repositories import UserRepository

router = Router()

WELCOME_TEXT = (
    "Merhaba. Ben senin kişisel AI koçunum.\n\n"
    "Kalıplarını hatırlarım, zorlandığında yanında olurum ve "
    "günden güne tutarlılık kurmana yardım ederim.\n\n"
    "Komutlar:\n"
    "/rapor — günlük durum raporu\n"
    "/durum — davranış içgörüleri\n"
    "/mod — koç tarzını değiştir\n"
    "/hatirla — seni ne kadar tanıdığım\n"
    "/veriler — verilerini indir\n"
    "/unut — hafızayı temizle\n"
    "/yardim — komut listesi\n\n"
    "Ya da doğrudan yaz — seninle sohbet edebilirim."
)


@router.message(CommandStart())
@router.message(Command("basla"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())
    if await needs_onboarding(session, user.id):
        await start_onboarding(message, state)
