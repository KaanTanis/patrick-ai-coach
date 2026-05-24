from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.setback import SetbackRecovery

router = Router()


@router.message(Command("zor", "setback"))
async def cmd_setback(message: Message, session: AsyncSession) -> None:
    await message.answer(
        "Ne olduğunu anlat. Gerilemeler sürecin bir parçası — birlikte toparlanırız."
    )


async def handle_setback_message(message: Message, session: AsyncSession) -> None:
    from app.repositories import UserRepository

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    recovery = SetbackRecovery(session)
    response = await recovery.handle(user.id, message.text, user.personality_key)
    await message.answer(response)
