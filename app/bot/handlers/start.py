from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard
from app.repositories import UserRepository

router = Router()

WELCOME_TEXT = (
    "Merhaba. Ben senin kişisel AI koçunum.\n\n"
    "Kalıplarını hatırlarım, utandırmadan toparlanmana destek olurum ve "
    "günden güne tutarlılık kurmana yardım ederim.\n\n"
    "Komutlar:\n"
    "/rapor — günlük durum raporu\n"
    "/durum — davranış içgörüleri\n"
    "/mod — koç tarzını değiştir\n"
    "/veriler — verilerini indir\n"
    "/unut — hafızayı temizle\n"
    "/yardim — komut listesi\n\n"
    "Ya da doğrudan yaz — seninle sohbet edebilirim."
)


@router.message(CommandStart())
@router.message(Command("basla"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    await users.get_or_create(
        telegram_id=message.from_user.id,
        name=message.from_user.full_name,
    )
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_keyboard())
