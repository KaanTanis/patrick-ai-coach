from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.food.vision_analyzer import FoodVisionAnalyzer
from app.config import get_settings

router = Router()
settings = get_settings()


@router.message(Command("yemek", "food"))
async def cmd_food(message: Message) -> None:
    await message.answer("Yemeğinin fotoğrafını gönder, analiz edeyim.")


@router.message(F.photo, StateFilter(None))
async def handle_food_photo(
    message: Message, session: AsyncSession, bot: Bot
) -> None:
    from pathlib import Path
    from uuid import uuid4

    from app.repositories import UserRepository

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await message.answer("Yemeğini analiz ediyorum...")

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    if not file.file_path:
        await message.answer("Fotoğraf indirilemedi. Lütfen tekrar dene.")
        return

    settings.photo_storage_path.mkdir(parents=True, exist_ok=True)
    dest = settings.photo_storage_path / f"{uuid4().hex}.jpg"
    await bot.download_file(file.file_path, dest)

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    analyzer = FoodVisionAnalyzer(session)
    response = await analyzer.analyze(user.id, Path(dest))
    await message.answer(response)


@router.message(F.photo)
async def food_photo_during_fsm(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current:
        await message.answer(
            "Şu an başka bir akıştasın. Bitir veya /iptal yaz, sonra yemek fotoğrafı gönder."
        )
