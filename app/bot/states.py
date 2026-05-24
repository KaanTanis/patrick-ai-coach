from aiogram.fsm.state import State, StatesGroup


class CheckInStates(StatesGroup):
    mood = State()
    sleep = State()
    energy = State()
    cravings = State()
    workout = State()
    workout_type = State()
    stress = State()
    weight = State()
    motivation = State()
    notes = State()


class ErasureStates(StatesGroup):
    confirm = State()


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
