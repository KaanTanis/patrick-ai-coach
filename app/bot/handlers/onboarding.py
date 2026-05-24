from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import OnboardingStates
from app.models import MemorySource, MemoryType
from app.repositories import MemoryRepository, UserRepository
from app.services.preferences import PreferencesService

router = Router()

SKIP = {"/skip", "skip", "atla", "/atla"}


async def needs_onboarding(session: AsyncSession, user_id: int) -> bool:
    prefs = PreferencesService(session)
    data = await prefs.get(user_id)
    return not data.get("onboarding_complete")


async def start_onboarding(message: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.sleep_window)
    await message.answer(
        "Hızlı kurulum (4 soru). Uyku penceren nedir?\n"
        "Örnek: 23:00-07:00 (atlamak için /skip)"
    )


@router.message(OnboardingStates.sleep_window)
async def onboarding_sleep(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.text or "").strip()
    sleep = None if text.lower() in SKIP else text
    await state.update_data(sleep_window=sleep)
    await state.set_state(OnboardingStates.main_goal)
    await message.answer("Şu anki en önemli hedefin ne? (tek cümle)")


@router.message(OnboardingStates.main_goal)
async def onboarding_goal(message: Message, state: FSMContext) -> None:
    await state.update_data(main_goal=(message.text or "").strip())
    await state.set_state(OnboardingStates.proactive_pref)
    await message.answer(
        "Proaktif hatırlatmalar göndereyim mi? (evet/hayır)"
    )


@router.message(OnboardingStates.proactive_pref)
async def onboarding_proactive(message: Message, state: FSMContext) -> None:
    text = (message.text or "").lower()
    proactive = text in {"evet", "e", "yes", "aç", "ac", "açık", "acik"}
    await state.update_data(proactive_nudges=proactive)
    await state.set_state(OnboardingStates.lens_pref)
    await message.answer(
        "Hangi perspektif sana daha yakın? jung | stoic | psych (veya /skip)"
    )


@router.message(OnboardingStates.lens_pref)
async def onboarding_lens(message: Message, state: FSMContext, session: AsyncSession) -> None:
    from sqlalchemy import update

    from app.models import User

    text = (message.text or "").strip().lower()
    lens = None if text in SKIP else text
    if lens not in {None, "jung", "stoic", "psych"}:
        await message.answer("jung, stoic veya psych yaz — ya da /skip")
        return

    data = await state.get_data()
    await state.clear()

    users = UserRepository(session)
    user = await users.get_or_create(message.from_user.id, message.from_user.full_name)

    schedule = dict(user.schedule or {})
    if data.get("sleep_window"):
        schedule["sleep_window"] = data["sleep_window"]

    personality = user.personality_key
    if lens == "jung":
        personality = "jungian"
    elif lens == "stoic":
        personality = "stoic_praxis"
    elif lens == "psych":
        personality = "psych_cbt"

    await session.execute(
        update(User)
        .where(User.id == user.id)
        .values(schedule=schedule or None, personality_key=personality)
    )

    prefs = PreferencesService(session)
    await prefs.update(
        user.id,
        {"onboarding_complete": True, "proactive_nudges": data.get("proactive_nudges", True)},
    )

    goal = data.get("main_goal")
    if goal:
        mem = MemoryRepository(session)
        await mem.create(
            user_id=user.id,
            memory_type=MemoryType.GOAL,
            content=goal,
            importance=0.9,
            source=MemorySource.MANUAL,
            metadata={"source": "onboarding"},
        )

    await message.answer(
        "Kurulum tamam. /rapor ile günlük rapor, /hatirla ile hafıza özetin.\n"
        "İstediğin zaman sohbet edebilirsin."
    )


@router.message(StateFilter(OnboardingStates))
async def onboarding_fallback(message: Message) -> None:
    await message.answer("Kurulumdasın — soruyu yanıtla veya /iptal ile atla.")
