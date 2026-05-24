from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.relapse import detect_relapse_intent
from app.ai.orchestrator import AIOrchestrator
from app.bot.commands_registry import MENU_BUTTONS

router = Router()


@router.message(F.text, StateFilter(None), ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def free_chat(message: Message, session: AsyncSession) -> None:
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    intent = "relapse" if detect_relapse_intent(message.text) else "free_chat"
    orchestrator = AIOrchestrator(session)
    result = await orchestrator.orchestrate(
        telegram_id=message.from_user.id,
        message=message.text,
        intent=intent,
        user_name=message.from_user.full_name,
    )
    await message.answer(result.text)
