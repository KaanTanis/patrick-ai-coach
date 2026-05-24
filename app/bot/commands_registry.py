from aiogram.types import BotCommand

# Reply keyboard button labels
BTN_REPORT = "📋 Rapor"
BTN_INSIGHTS = "💡 Durum"
BTN_PERSONALITY = "🎭 Mod"
BTN_HELP = "❓ Yardım"
BTN_ANALYSIS = "🧠 Analiz"
BTN_DREAM = "🌙 Rüya"
BTN_STOIC = "🏛 Stoic"
BTN_THOUGHT = "💭 Düşünce"

MENU_BUTTONS = {
    BTN_REPORT,
    BTN_INSIGHTS,
    BTN_PERSONALITY,
    BTN_HELP,
    BTN_ANALYSIS,
    BTN_DREAM,
    BTN_STOIC,
    BTN_THOUGHT,
}

BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="basla", description="Botu başlat"),
    BotCommand(command="rapor", description="Günlük durum raporu"),
    BotCommand(command="durum", description="Davranış içgörüleri"),
    BotCommand(command="mod", description="Koç tarzını değiştir"),
    BotCommand(command="lens", description="Tek seferlik perspektif lensi"),
    BotCommand(command="ruya", description="Rüya günlüğü"),
    BotCommand(command="golge", description="Gölge anı kaydı"),
    BotCommand(command="sabah", description="Stoik sabah ritüeli"),
    BotCommand(command="aksam", description="Stoik akşam muhasebesi"),
    BotCommand(command="dusunce", description="CBT düşünce kaydı"),
    BotCommand(command="duygu", description="Hızlı duygu check-in"),
    BotCommand(command="analiz", description="Derin çok lensli analiz"),
    BotCommand(command="serbest", description="Serbest mod aç/kapa"),
    BotCommand(command="geri", description="Gerileme bildir"),
    BotCommand(command="yemek", description="Öğün fotoğrafı analizi"),
    BotCommand(command="yardim", description="Komut listesi"),
    BotCommand(command="veriler", description="Verilerini dışa aktar"),
    BotCommand(command="unut", description="Hafızayı temizle"),
    BotCommand(command="sil", description="Tüm verileri kalıcı sil"),
    BotCommand(command="hatirla", description="Bot seni ne kadar tanıyor"),
    BotCommand(command="iptal", description="Aktif işlemi iptal et"),
]
