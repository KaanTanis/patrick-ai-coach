from app.bot.commands_registry import BOT_COMMANDS, BTN_HELP, BTN_INSIGHTS, BTN_REPORT


def test_turkish_commands_registered():
    commands = {c.command for c in BOT_COMMANDS}
    assert "rapor" in commands
    assert "durum" in commands
    assert "mod" in commands
    assert "geri" in commands
    assert "iptal" in commands
    assert "yardim" in commands
    assert "hatirla" in commands


def test_menu_buttons_turkish():
    assert "Rapor" in BTN_REPORT
    assert "Durum" in BTN_INSIGHTS
    assert "Yardım" in BTN_HELP
