from app.ai.model_router import pick_chat_model


def test_simple_message_uses_mini():
    assert pick_chat_model("merhaba", "free_chat") == "gpt-4o-mini"


def test_long_message_uses_full_model():
    text = "bugün çok zor bir gün geçirdim " * 10
    assert pick_chat_model(text, "free_chat") == "gpt-4o"


def test_setback_uses_full_model():
    assert pick_chat_model("geriledim", "setback") == "gpt-4o"


def test_complex_question_uses_full_model():
    text = "Geçen hafta söylediğim gibi stresli bir dönemdeyim — ne yapmalıyım?"
    assert pick_chat_model(text, "free_chat") == "gpt-4o"
