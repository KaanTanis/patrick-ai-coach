from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.behavioral.setback import SetbackRecovery
from app.bot.states import SetbackStates
from app.repositories import UserRepository

router = Router()

SKIP_TEXTS = {"/skip", "skip", "atla", "/atla", "yok", "hayır", "hayir"}


@router.message(Command("zor", "setback"))
async def cmd_setback(message: Message, state: FSMContext) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        await state.set_state(SetbackStates.trigger)
        await state.update_data(description=parts[1].strip())
        await message.answer(
            "Anladım. Bunu tetikleyen bir şey var mı? (yoksa /skip yaz)"
        )
        return

    await state.set_state(SetbackStates.description)
    await message.answer(
        "Ne olduğunu anlat. Gerilemeler sürecin bir parçası — birlikte toparlanırız."
    )


@router.message(SetbackStates.description)
async def setback_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(SetbackStates.trigger)
    await message.answer("Bunu tetikleyen bir şey var mı? (yoksa /skip yaz)")


@router.message(SetbackStates.trigger)
async def setback_trigger(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    trigger = None if text.lower() in SKIP_TEXTS else text
    await state.update_data(trigger=trigger)
    await state.set_state(SetbackStates.action)
    await message.answer("Şimdi atabileceğin küçük bir adım ne olabilir? (15 dk, bugün yapılabilir)")


@router.message(SetbackStates.action)
async def setback_action(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    recovery = SetbackRecovery(session)
    response = await recovery.complete_flow(
        user_id=user.id,
        description=data.get("description", ""),
        trigger=data.get("trigger"),
        micro_action=(message.text or "").strip(),
        personality_key=user.personality_key,
        telegram_id=user.telegram_id,
    )
    await message.answer(response)


@router.message(StateFilter(SetbackStates))
async def setback_fallback(message: Message) -> None:
    await message.answer("Gerileme akışındasın. Yanıt ver veya /iptal yaz.")
