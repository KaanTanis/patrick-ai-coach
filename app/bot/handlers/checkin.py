from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import rating_keyboard, skip_keyboard, yes_no_keyboard
from app.bot.states import CheckInStates
from app.repositories import UserRepository
from app.services.checkin import CheckInService

router = Router()

SKIP_TEXTS = {"/skip", "skip", "atla", "/atla"}


async def _start_checkin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CheckInStates.mood)
    await message.answer(
        "8 soruluk rapor başlıyor. Bitirmeden çıkmak için /iptal yaz.\n\n"
        "Bugün ruh halin nasıl? (1-10)",
        reply_markup=rating_keyboard("mood"),
    )


async def _finalize_checkin(
    message: Message, state: FSMContext, session: AsyncSession, notes: str | None
) -> None:
    data = await state.get_data()
    data["notes"] = notes
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    service = CheckInService(session)
    check_in = await service.save_checkin(user.id, data, timezone=user.timezone)
    await message.answer("Raporun kaydedildi.")

    insight = await service.generate_insight(user.id, check_in)
    if insight:
        await message.answer(insight)


@router.message(Command("rapor", "checkin"))
async def cmd_checkin(message: Message, state: FSMContext) -> None:
    await _start_checkin(message, state)


@router.callback_query(F.data == "checkin:start")
async def callback_checkin_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _start_checkin(callback.message, state)


@router.callback_query(CheckInStates.mood, F.data.startswith("mood:"))
async def process_mood(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(mood=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.sleep)
    await callback.message.edit_text(
        "Dün gece uyku kaliten nasıldı? (1-10)", reply_markup=rating_keyboard("sleep")
    )


@router.callback_query(CheckInStates.sleep, F.data.startswith("sleep:"))
async def process_sleep(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(sleep_quality=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.energy)
    await callback.message.edit_text(
        "Şu anki enerji seviyen? (1-10)", reply_markup=rating_keyboard("energy")
    )


@router.callback_query(CheckInStates.energy, F.data.startswith("energy:"))
async def process_energy(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(energy=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.cravings)
    await callback.message.edit_text(
        "Bugün sigara isteği ne kadar? (1-10)", reply_markup=rating_keyboard("cravings")
    )


@router.callback_query(CheckInStates.cravings, F.data.startswith("cravings:"))
async def process_cravings(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(smoking_craving=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.workout)
    await callback.message.edit_text(
        "Bugün antrenman yaptın mı?", reply_markup=yes_no_keyboard("workout")
    )


@router.callback_query(CheckInStates.workout, F.data.startswith("workout:"))
async def process_workout(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    done = callback.data.split(":")[1] == "yes"
    await state.update_data(workout_done=done)
    if done:
        await state.set_state(CheckInStates.workout_type)
        await callback.message.edit_text("Ne tür antrenman yaptın? (mesaj olarak yaz)")
    else:
        await state.update_data(workout_type=None)
        await state.set_state(CheckInStates.stress)
        await callback.message.edit_text(
            "Bugün stres seviyen? (1-10)", reply_markup=rating_keyboard("stress")
        )


@router.message(CheckInStates.workout_type)
async def process_workout_type(message: Message, state: FSMContext) -> None:
    await state.update_data(workout_type=message.text)
    await state.set_state(CheckInStates.stress)
    await message.answer("Bugün stres seviyen? (1-10)", reply_markup=rating_keyboard("stress"))


@router.callback_query(CheckInStates.stress, F.data.startswith("stress:"))
async def process_stress(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(stress=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.weight)
    await callback.message.edit_text(
        "Bugünkü kilon? (kg olarak yaz veya Atla'ya bas)",
        reply_markup=skip_keyboard("weight"),
    )


@router.callback_query(CheckInStates.weight, F.data == "weight:skip")
async def skip_weight(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(weight=None)
    await state.set_state(CheckInStates.motivation)
    await callback.message.edit_text(
        "Motivasyon seviyen? (1-10)", reply_markup=rating_keyboard("motivation")
    )


@router.message(CheckInStates.weight)
async def process_weight(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.replace(",", "."))
        await state.update_data(weight=weight)
    except ValueError:
        await message.answer("Lütfen bir sayı gir veya Atla'yı kullan.")
        return
    await state.set_state(CheckInStates.motivation)
    await message.answer("Motivasyon seviyen? (1-10)", reply_markup=rating_keyboard("motivation"))


@router.callback_query(CheckInStates.motivation, F.data.startswith("motivation:"))
async def process_motivation(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(motivation=int(callback.data.split(":")[1]))
    await state.set_state(CheckInStates.notes)
    await callback.message.edit_text(
        "Eklemek istediğin bir not var mı?",
        reply_markup=skip_keyboard("notes"),
    )


@router.callback_query(CheckInStates.notes, F.data == "notes:skip")
async def skip_notes(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await callback.answer()
    await _finalize_checkin(callback.message, state, session, notes=None)


@router.message(CheckInStates.notes)
async def process_notes(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    text = (message.text or "").strip()
    notes = None if text.lower() in SKIP_TEXTS else message.text
    await _finalize_checkin(message, state, session, notes=notes)


@router.message(StateFilter(CheckInStates))
async def checkin_fsm_fallback(message: Message) -> None:
    await message.answer("Rapor akışındasın. Soruları yanıtla veya /iptal yaz.")
