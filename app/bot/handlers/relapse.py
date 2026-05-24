from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.relapse import RelapseRecovery

router = Router()


@router.message(Command("geri", "relapse"))
async def cmd_relapse(message: Message, session: AsyncSession) -> None:
    await message.answer(
        "Ne olduğunu anlat. Yargı yok — gerilemeler sürecin bir parçası."
    )


async def handle_relapse_message(message: Message, session: AsyncSession) -> None:
    from app.repositories import UserRepository

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    recovery = RelapseRecovery(session)
    response = await recovery.handle(user.id, message.text)
    await message.answer(response)
