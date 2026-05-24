from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.commands_registry import (
    BTN_ANALYSIS,
    BTN_DREAM,
    BTN_HELP,
    BTN_INSIGHTS,
    BTN_PERSONALITY,
    BTN_REPORT,
    BTN_STOIC,
    BTN_THOUGHT,
)
from app.bot.handlers.checkin import _start_checkin
from app.bot.handlers.commands import cmd_help
from app.bot.handlers.insights import cmd_insights
from app.bot.handlers.personality import cmd_personality
from app.bot.handlers.psych import cmd_thought
from app.bot.handlers.stoic_ritual import cmd_morning

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


@router.message(F.text == BTN_ANALYSIS)
async def btn_analysis(message: Message, session: AsyncSession) -> None:
    from app.ai.analysis.deep_analyzer import DeepAnalyzer
    from app.repositories import UserRepository

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    result = await DeepAnalyzer(session).analyze(user.id, lens="all", days=7)
    if result:
        await message.answer(result)


@router.message(F.text == BTN_DREAM)
async def btn_dream(message: Message) -> None:
    await message.answer("Rüyanı anlat:\n/ruya <rüya metni>")


@router.message(F.text == BTN_STOIC)
async def btn_stoic(message: Message, state: FSMContext) -> None:
    await cmd_morning(message, state)


@router.message(F.text == BTN_THOUGHT)
async def btn_thought(message: Message, state: FSMContext) -> None:
    await cmd_thought(message, state)
