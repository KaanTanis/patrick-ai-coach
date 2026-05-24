from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router()


@router.message(Command("iptal"))
@router.message(F.text.lower().in_({"iptal", "vazgeç", "vazgec"}))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("İptal edilecek aktif bir işlem yok.")
        return
    await state.clear()
    await message.answer("Tamam, sohbete döndük. Ne hakkında konuşmak istersin?")
