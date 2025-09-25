from aiogram.fsm.state import StatesGroup, State


class ParseStates(StatesGroup):
    waiting_for_file = State()
    validating = State()
    normalizing = State()
    saving = State()
