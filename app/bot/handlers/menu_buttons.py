from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.commands_registry import BTN_HELP, BTN_INSIGHTS, BTN_PERSONALITY, BTN_REPORT
from app.bot.handlers.checkin import _start_checkin
from app.bot.handlers.commands import cmd_help
from app.bot.handlers.insights import cmd_insights
from app.bot.handlers.personality import cmd_personality

router = Router()


@router.message(F.text == BTN_REPORT)
async def btn_report(message: Message, state: FSMContext) -> None:
    await _start_checkin(message, state)


@router.message(F.text == BTN_INSIGHTS)
async def btn_insights(message: Message, session: AsyncSession) -> None:
    await cmd_insights(message, session)


@router.message(F.text == BTN_PERSONALITY)
async def btn_personality(message: Message, session: AsyncSession) -> None:
    await cmd_personality(message, session)


@router.message(F.text == BTN_HELP)
async def btn_help(message: Message) -> None:
    await cmd_help(message)
