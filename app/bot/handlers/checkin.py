from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interview.composer import InterviewComposer
from app.ai.interview.stop_phrases import is_stop_phrase
from app.bot.keyboards import rating_keyboard, skip_keyboard, yes_no_keyboard
from app.bot.states import CheckInStates
from app.models import MemorySource, MemoryType
from app.repositories import MemoryRepository, UserRepository
from app.services.checkin import CheckInService

router = Router()

SKIP_TEXTS = {"/skip", "skip", "atla", "/atla"}
PARTIAL_ACK = "Tamam, şimdilik bu kadar. Yanıtladıklarını kaydettim."

STEP_FIELD_MAP = {
    "mood": "mood",
    "sleep": "sleep_quality",
    "energy": "energy",
    "stress": "stress",
    "motivation": "motivation",
    "weight": "weight",
    "notes": "notes",
}


def _answers_to_checkin(answers: dict) -> dict:
    data: dict = {}
    for step, field in STEP_FIELD_MAP.items():
        if step in answers and answers[step] is not None:
            data[field] = answers[step]
    if "workout" in answers:
        data["workout_done"] = answers["workout"]
        if answers.get("workout_type"):
            data["workout_type"] = answers["workout_type"]
    return data


async def save_partial_checkin(
    message: Message, state: FSMContext, session: AsyncSession
) -> bool:
    """Save partial check-in answers if any. Returns True if state was check-in."""
    current = await state.get_state()
    if not current or not current.endswith(":adaptive"):
        return False
    data = await state.get_data()
    answers = data.get("answers", {})
    if answers:
        await _save_partial(message, state, session, answers)
    else:
        await state.clear()
        await message.answer("Tamam, sohbete döndük. Ne hakkında konuşmak istersin?")
    return True


async def _sync_workout_record(
    session: AsyncSession, user_id: int, answers: dict
) -> None:
    if not answers.get("workout"):
        return
    from app.repositories import WorkoutRepository

    workouts = WorkoutRepository(session)
    await workouts.create(
        user_id,
        {
            "type": answers.get("workout_type"),
            "completed": True,
        },
    )


async def _save_partial(
    message: Message, state: FSMContext, session: AsyncSession, answers: dict
) -> None:
    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    data = _answers_to_checkin(answers)
    if data:
        service = CheckInService(session)
        await service.save_checkin(user.id, data, timezone=user.timezone)
        summary = ", ".join(f"{k}={v}" for k, v in data.items())
        mem = MemoryRepository(session)
        await mem.create(
            user_id=user.id,
            memory_type=MemoryType.EPISODE,
            content=f"Kısmi rapor: {summary[:400]}",
            importance=0.6,
            source=MemorySource.MANUAL,
            metadata={"type": "partial_checkin"},
        )
    await state.clear()
    await message.answer(PARTIAL_ACK)


async def _ask_current(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    steps = data["steps"]
    index = data["index"]
    answers = data.get("answers", {})
    step = steps[index]

    composer = InterviewComposer(session)
    text = await composer.phrase_question(step, answers, index, len(steps))
    kind = composer.step_kind(step)

    if kind == "rating":
        await message.answer(text, reply_markup=rating_keyboard(step))
    elif kind == "yes_no":
        await message.answer(text, reply_markup=yes_no_keyboard(step))
    elif step == "weight":
        await message.answer(text, reply_markup=skip_keyboard(step))
    else:
        await message.answer(text, reply_markup=skip_keyboard(step) if step == "notes" else None)


async def _advance_or_finish(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    index = data["index"] + 1
    if index >= len(data["steps"]):
        await _finalize_checkin(message, state, session)
        return
    await state.update_data(index=index)
    await _ask_current(message, state, session)


async def _finalize_checkin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    answers = data.get("answers", {})
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    checkin_data = _answers_to_checkin(answers)

    service = CheckInService(session)
    check_in = await service.save_checkin(user.id, checkin_data, timezone=user.timezone)
    await _sync_workout_record(session, user.id, answers)
    await message.answer("Raporun kaydedildi.")

    insight = await service.generate_insight(user.id, check_in)
    if insight:
        await message.answer(insight)


async def _start_checkin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    composer = InterviewComposer(session)
    steps = await composer.plan_steps(user.id)

    await state.set_state(CheckInStates.adaptive)
    await state.update_data(steps=steps, index=0, answers={}, awaiting_workout_type=False)
    await message.answer(
        f"Kısa rapor — {len(steps)} soru. İstediğin zaman \"bu kadar soru yeter\" diyebilirsin.\n"
        "Bitirmeden çıkmak için /iptal yaz."
    )
    await _ask_current(message, state, session)


@router.message(Command("rapor", "checkin"))
async def cmd_checkin(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _start_checkin(message, state, session)


@router.callback_query(F.data == "checkin:start")
async def callback_checkin_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    await _start_checkin(callback.message, state, session)


@router.message(CheckInStates.adaptive)
async def adaptive_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if is_stop_phrase(message.text or ""):
        data = await state.get_data()
        await _save_partial(message, state, session, data.get("answers", {}))
        return

    data = await state.get_data()
    if data.get("awaiting_workout_type"):
        answers = data.get("answers", {})
        answers["workout_type"] = message.text
        await state.update_data(answers=answers, awaiting_workout_type=False)
        await _advance_or_finish(message, state, session)
        return

    steps = data["steps"]
    step = steps[data["index"]]
    text = (message.text or "").strip()

    if step == "weight":
        if text.lower() in SKIP_TEXTS:
            answers = data.get("answers", {})
            answers["weight"] = None
            await state.update_data(answers=answers)
            await _advance_or_finish(message, state, session)
            return
        try:
            weight = float(text.replace(",", "."))
            answers = data.get("answers", {})
            answers["weight"] = weight
            await state.update_data(answers=answers)
            await _advance_or_finish(message, state, session)
        except ValueError:
            await message.answer("Lütfen bir sayı gir veya Atla'yı kullan.")
        return

    if step == "notes":
        answers = data.get("answers", {})
        answers["notes"] = None if text.lower() in SKIP_TEXTS else message.text
        await state.update_data(answers=answers)
        await _finalize_checkin(message, state, session)
        return

    await message.answer("Lütfen butonları kullan veya /iptal yaz.")


@router.callback_query(CheckInStates.adaptive, F.data.contains(":"))
async def adaptive_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    data = await state.get_data()
    steps = data["steps"]
    step = steps[data["index"]]
    prefix, value = callback.data.split(":", 1)

    if prefix != step and not (step == "workout" and prefix == "workout"):
        return

    answers = data.get("answers", {})

    if step in {"mood", "sleep", "energy", "stress", "motivation"}:
        answers[step] = int(value)
        await state.update_data(answers=answers)
        await callback.message.edit_text(f"Kaydedildi: {value}/10")
        await _advance_or_finish(callback.message, state, session)
        return

    if step == "workout":
        done = value == "yes"
        answers["workout"] = done
        if done:
            await state.update_data(answers=answers, awaiting_workout_type=True)
            await callback.message.edit_text("Ne tür hareket yaptın? (mesaj olarak yaz)")
        else:
            answers["workout_type"] = None
            await state.update_data(answers=answers)
            await _advance_or_finish(callback.message, state, session)
        return

    if step == "weight" and value == "skip":
        answers["weight"] = None
        await state.update_data(answers=answers)
        await callback.message.edit_text("Kilo atlandı.")
        await _advance_or_finish(callback.message, state, session)
        return

    if step == "notes" and value == "skip":
        answers["notes"] = None
        await state.update_data(answers=answers)
        await _finalize_checkin(callback.message, state, session)


@router.message(StateFilter(CheckInStates.adaptive))
async def checkin_fsm_fallback(message: Message) -> None:
    await message.answer("Rapor akışındasın. Soruları yanıtla veya /iptal yaz.")
