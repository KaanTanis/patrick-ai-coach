from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_client import get_openai_client
from app.ai.personalities.lenses import CRISIS_KEYWORDS, CRISIS_RESPONSE
from app.bot.keyboards import rating_keyboard, skip_keyboard
from app.bot.states import EmotionCheckinStates, ThoughtRecordStates
from app.repositories import UserRepository
from app.repositories.philosophy import EmotionRepository, ThoughtRepository

router = Router()

THERAPY_DISCLAIMER = "\n\n_Bu bir terapi seansı değil — kişisel koçluk aracı._"


def _crisis_in(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)


@router.message(Command("dusunce", "thought"))
async def cmd_thought(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ThoughtRecordStates.situation)
    await message.answer("Düşünce kaydı.\n\n1/5 — Durum: Ne oldu?")


@router.message(ThoughtRecordStates.situation)
async def tr_situation(message: Message, state: FSMContext) -> None:
    if _crisis_in(message.text):
        await state.clear()
        await message.answer(CRISIS_RESPONSE)
        return
    await state.update_data(situation=message.text)
    await state.set_state(ThoughtRecordStates.automatic_thought)
    await message.answer("2/5 — Otomatik düşünce: Aklından geçen ne?")


@router.message(ThoughtRecordStates.automatic_thought)
async def tr_automatic(message: Message, state: FSMContext) -> None:
    if _crisis_in(message.text):
        await state.clear()
        await message.answer(CRISIS_RESPONSE)
        return
    await state.update_data(automatic_thought=message.text)
    await state.set_state(ThoughtRecordStates.emotion)
    await message.answer("3/5 — Duygu adı (ör. kaygı, öfke):")


@router.message(ThoughtRecordStates.emotion)
async def tr_emotion(message: Message, state: FSMContext) -> None:
    await state.update_data(emotion=message.text)
    await message.answer(
        "Duygu şiddeti (1-10):",
        reply_markup=rating_keyboard("tr_intensity"),
    )


@router.callback_query(ThoughtRecordStates.emotion, F.data.startswith("tr_intensity:"))
async def tr_intensity(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    intensity = int(callback.data.split(":")[1])
    await state.update_data(emotion_intensity=intensity)
    await state.set_state(ThoughtRecordStates.evidence_for)
    await callback.message.edit_text(f"Şiddet: {intensity}/10\n\n4/5 — Bu düşünceyi destekleyen kanıtlar?")


@router.message(ThoughtRecordStates.evidence_for)
async def tr_evidence_for(message: Message, state: FSMContext) -> None:
    await state.update_data(evidence_for=message.text)
    await state.set_state(ThoughtRecordStates.evidence_against)
    await message.answer("Kanıt aleyh — düşünceye karşı ne var?")


@router.message(ThoughtRecordStates.evidence_against)
async def tr_evidence_against(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    data["evidence_against"] = message.text

    prompt = f"""CBT düşünce kaydı için dengeli alternatif düşünce öner.
Teşhis yok. 1-2 cümle Türkçe.

Durum: {data.get('situation')}
Otomatik düşünce: {data.get('automatic_thought')}
Duygu: {data.get('emotion')} ({data.get('emotion_intensity')}/10)
Kanıt: {data.get('evidence_for')}
Kanıt aleyh: {data.get('evidence_against')}"""

    suggestion = await get_openai_client().chat(
        [{"role": "user", "content": prompt}], model="gpt-4o-mini", max_tokens=150
    )
    await state.update_data(balanced_suggestion=suggestion)
    await state.set_state(ThoughtRecordStates.balanced)
    await message.answer(
        f"5/5 — Dengeli alternatif düşünce:\n\nÖneri: _{suggestion}_\n\n"
        "Kabul et veya kendi cümleni yaz:",
        parse_mode="Markdown",
    )


@router.message(ThoughtRecordStates.balanced)
async def tr_balanced(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    balanced = message.text.strip()
    if balanced.lower() in {"evet", "kabul", "tamam", "ok"}:
        balanced = data.get("balanced_suggestion", balanced)
    data["balanced_thought"] = balanced
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)
    repo = ThoughtRepository(session)
    await repo.create(user.id, data)

    await message.answer(
        f"Düşünce kaydın tamam.\n\nDengeli düşünce: {balanced}{THERAPY_DISCLAIMER}",
        parse_mode="Markdown",
    )


@router.message(Command("duygu", "emotion"))
async def cmd_emotion(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(EmotionCheckinStates.emotion)
    await message.answer("Hızlı duygu check-in.\n\nŞu an ne hissediyorsun?")


@router.message(EmotionCheckinStates.emotion)
async def ec_emotion(message: Message, state: FSMContext) -> None:
    if _crisis_in(message.text):
        await state.clear()
        await message.answer(CRISIS_RESPONSE)
        return
    await state.update_data(emotion=message.text)
    await message.answer("Şiddet (1-10):", reply_markup=rating_keyboard("ec_intensity"))


@router.callback_query(EmotionCheckinStates.emotion, F.data.startswith("ec_intensity:"))
async def ec_intensity(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    intensity = int(callback.data.split(":")[1])
    await state.update_data(intensity=intensity)
    await state.set_state(EmotionCheckinStates.body)
    await callback.message.edit_text(
        "Bedensel his (opsiyonel):",
        reply_markup=skip_keyboard("ec_body"),
    )


@router.callback_query(EmotionCheckinStates.body, F.data == "ec_body:skip")
async def ec_body_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await callback.answer()
    await _finish_emotion(callback.message, state, session, body=None)


@router.message(EmotionCheckinStates.body)
async def ec_body(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await _finish_emotion(message, state, session, body=message.text)


async def _finish_emotion(
    message: Message, state: FSMContext, session: AsyncSession, body: str | None
) -> None:
    data = await state.get_data()
    data["body_sensation"] = body
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    prompt = f"""Kısa duygu yansıtması yap (2-3 cümle Türkçe) + bir açık soru sor.
Terapist tonu ama gerçek terapi değil.

Duygu: {data.get('emotion')} ({data.get('intensity')}/10)
Bedensel: {body or 'belirtilmedi'}"""

    reflection = await get_openai_client().chat(
        [{"role": "user", "content": prompt}], model="gpt-4o-mini", max_tokens=200
    )
    data["ai_reflection"] = reflection

    repo = EmotionRepository(session)
    await repo.create(user.id, data)
    await message.answer(reflection)
