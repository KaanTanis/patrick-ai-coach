from app.bot.commands_registry import BOT_COMMANDS, BTN_ANALYSIS, BTN_DREAM, BTN_STOIC, BTN_THOUGHT
from app.bot.handlers.personality import PERSONALITY_KEYS
from app.services.lens import VALID_LENSES


def test_personality_keys_eight_mods():
    assert len(PERSONALITY_KEYS) == 8
    assert "stoic_praxis" in PERSONALITY_KEYS
    assert "jung_shadow" in PERSONALITY_KEYS
    assert "psych_cbt" in PERSONALITY_KEYS


def test_philosophy_commands_registered():
    commands = {c.command for c in BOT_COMMANDS}
    for cmd in ("lens", "ruya", "golge", "sabah", "aksam", "dusunce", "duygu", "analiz", "serbest"):
        assert cmd in commands


def test_lens_valid_keys():
    assert VALID_LENSES == {"jung", "stoic", "psych"}


def test_menu_philosophy_buttons():
    assert "Analiz" in BTN_ANALYSIS
    assert "Rüya" in BTN_DREAM
    assert "Stoic" in BTN_STOIC
    assert "Düşünce" in BTN_THOUGHT
