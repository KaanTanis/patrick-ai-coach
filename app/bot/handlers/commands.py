from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("yardim", "help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Komutlar:\n"
        "/rapor — ruh hali, uyku, enerji, istek, antrenman, stres, kilo, motivasyon\n"
        "/durum — son davranış içgörüleri\n"
        "/mod <anahtar> — stoic, therapist, coach, jungian, companion\n"
        "/geri — gerileme bildir\n"
        "/veriler — tüm verilerini JSON olarak indir\n"
        "/unut [tür] — hafızayı temizle\n"
        "/hatirla — bot seni ne kadar tanıyor\n"
        "/yemek — öğün kaydet (veya fotoğraf gönder)\n"
        "/iptal — aktif rapor/check-in işlemini iptal et\n\n"
        "Ya da sadece sohbet et — bağlamı ve kalıpları zamanla hatırlarım."
    )
