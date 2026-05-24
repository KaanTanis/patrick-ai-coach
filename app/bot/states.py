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
