from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import skip_keyboard
from app.bot.states import StoicEveningStates, StoicMorningStates
from app.repositories import UserRepository
from app.repositories.philosophy import StoicRitualRepository

router = Router()


@router.message(Command("sabah", "morning"))
async def cmd_morning(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StoicMorningStates.control)
    await message.answer(
        "Stoik sabah ritüeli.\n\n"
        "Bugün kontrol edebileceğin 1-3 şeyi yaz (virgülle ayırabilirsin):",
        reply_markup=skip_keyboard("stoic_m_control"),
    )


@router.callback_query(StoicMorningStates.control, F.data == "stoic_m_control:skip")
async def skip_m_control(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(control_items=[])
    await state.set_state(StoicMorningStates.premeditatio)
    await callback.message.edit_text(
        "Olası bir zorluğu önceden düşün (premeditatio). Atlayabilirsin.",
        reply_markup=skip_keyboard("stoic_m_pre"),
    )


@router.message(StoicMorningStates.control)
async def process_m_control(message: Message, state: FSMContext) -> None:
    items = [i.strip() for i in message.text.split(",") if i.strip()]
    await state.update_data(control_items=items)
    await state.set_state(StoicMorningStates.premeditatio)
    await message.answer(
        "Olası bir zorluğu önceden düşün (premeditatio):",
        reply_markup=skip_keyboard("stoic_m_pre"),
    )


@router.callback_query(StoicMorningStates.premeditatio, F.data == "stoic_m_pre:skip")
async def skip_m_pre(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(premeditatio=None)
    await state.set_state(StoicMorningStates.intention)
    await callback.message.edit_text("Günün erdem niyeti — tek cümle:")


@router.message(StoicMorningStates.premeditatio)
async def process_m_pre(message: Message, state: FSMContext) -> None:
    await state.update_data(premeditatio=message.text)
    await state.set_state(StoicMorningStates.intention)
    await message.answer("Günün erdem niyeti — tek cümle:")


@router.message(StoicMorningStates.intention)
async def finish_morning(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    data["virtue_intention"] = message.text
    data["ritual_type"] = "morning"
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    repo = StoicRitualRepository(session)
    await repo.create(user.id, data)

    summary = (
        f"Sabah ritüelin kaydedildi.\n"
        f"Kontrol: {', '.join(data.get('control_items') or []) or '—'}\n"
        f"Niyet: {data.get('virtue_intention')}"
    )
    await message.answer(summary)


@router.message(Command("aksam", "evening"))
async def cmd_evening(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StoicEveningStates.good)
    await message.answer("Stoik akşam muhasebesi.\n\nBugün ne iyi gitti?")


@router.message(StoicEveningStates.good)
async def process_e_good(message: Message, state: FSMContext) -> None:
    await state.update_data(evening_good=message.text)
    await state.set_state(StoicEveningStates.hard)
    await message.answer("Ne zorladı?")


@router.message(StoicEveningStates.hard)
async def process_e_hard(message: Message, state: FSMContext) -> None:
    await state.update_data(evening_hard=message.text)
    await state.set_state(StoicEveningStates.dichotomy)
    await message.answer("Neyi kontrol edemedin — nasıl bıraktın veya bırakabilirdin?")


@router.message(StoicEveningStates.dichotomy)
async def process_e_dichotomy(message: Message, state: FSMContext) -> None:
    await state.update_data(dichotomy_audit=message.text)
    await state.set_state(StoicEveningStates.tomorrow)
    await message.answer("Yarın için tek mikro niyet:")


@router.message(StoicEveningStates.tomorrow)
async def finish_evening(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    data["tomorrow_intention"] = message.text
    data["ritual_type"] = "evening"
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    repo = StoicRitualRepository(session)
    await repo.create(user.id, data)
    await message.answer("Akşam muhaseben kaydedildi. İyi geceler.")
