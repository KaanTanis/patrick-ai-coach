from app.repositories import _time_of_day_label


def test_time_of_day_labels():
    assert _time_of_day_label(8) == "sabah"
    assert _time_of_day_label(12) == "öğle"
    assert _time_of_day_label(18) == "akşam"
    assert _time_of_day_label(23) == "gece"


def test_commands_include_hatirla():
    from app.bot.commands_registry import BOT_COMMANDS

    commands = {c.command for c in BOT_COMMANDS}
    assert "hatirla" in commands
