from aiogram.fsm.state import State, StatesGroup


class CheckInStates(StatesGroup):
    adaptive = State()


class ErasureStates(StatesGroup):
    confirm = State()


class SetbackStates(StatesGroup):
    description = State()
    trigger = State()
    action = State()


class OnboardingStates(StatesGroup):
    sleep_window = State()
    main_goal = State()
    proactive_pref = State()
    lens_pref = State()


class StoicMorningStates(StatesGroup):
    control = State()
    premeditatio = State()
    intention = State()


class StoicEveningStates(StatesGroup):
    good = State()
    hard = State()
    dichotomy = State()
    tomorrow = State()


class ThoughtRecordStates(StatesGroup):
    situation = State()
    automatic_thought = State()
    emotion = State()
    evidence_for = State()
    evidence_against = State()
    balanced = State()


class EmotionCheckinStates(StatesGroup):
    emotion = State()
    intensity = State()
    body = State()
