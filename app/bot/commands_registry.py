from aiogram.types import BotCommand

# Reply keyboard button labels
BTN_REPORT = "📋 Rapor"
BTN_INSIGHTS = "💡 Durum"
BTN_PERSONALITY = "🎭 Mod"
BTN_HELP = "❓ Yardım"

MENU_BUTTONS = {BTN_REPORT, BTN_INSIGHTS, BTN_PERSONALITY, BTN_HELP}

BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="basla", description="Botu başlat"),
    BotCommand(command="rapor", description="Günlük durum raporu"),
    BotCommand(command="durum", description="Davranış içgörüleri"),
    BotCommand(command="mod", description="Koç tarzını değiştir"),
    BotCommand(command="geri", description="Gerileme bildir"),
    BotCommand(command="yemek", description="Öğün fotoğrafı analizi"),
    BotCommand(command="yardim", description="Komut listesi"),
    BotCommand(command="veriler", description="Verilerini dışa aktar"),
    BotCommand(command="unut", description="Hafızayı temizle"),
    BotCommand(command="hatirla", description="Bot seni ne kadar tanıyor"),
    BotCommand(command="iptal", description="Aktif işlemi iptal et"),
]
