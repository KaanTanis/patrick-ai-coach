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
        "/mod <anahtar> — kişilik modu (stoic, jungian, psych_cbt, ...)\n"
        "/lens jung|stoic|psych — sonraki mesaja tek seferlik lens\n"
        "/ruya <metin> — rüya günlüğü + Jung yorumu\n"
        "/golge <metin> — gölge anı kaydı\n"
        "/sabah — stoik sabah ritüeli\n"
        "/aksam — stoik akşam muhasebesi\n"
        "/dusunce — CBT düşünce kaydı\n"
        "/duygu — hızlı duygu check-in\n"
        "/analiz [jung|stoic|psych] [7|30] — derin analiz\n"
        "/serbest ac|kapa — serbest keşif modu\n"
        "/geri — gerileme bildir\n"
        "/veriler — tüm verilerini JSON olarak indir\n"
        "/unut [tür] — hafızayı temizle\n"
        "/sil — tüm verileri kalıcı sil\n"
        "/hatirla — bot seni ne kadar tanıyor\n"
        "/yemek — öğün kaydet (veya fotoğraf gönder)\n"
        "/iptal — aktif rapor/ritüel/kayıt işlemini iptal et\n\n"
        "Ya da sadece sohbet et — bağlamı ve kalıpları zamanla hatırlarım."
    )
