from app.ai.model_router import pick_chat_model
from app.ai.model_settings import chat_model, fast_model


def test_short_message_uses_fast_model():
    assert pick_chat_model("merhaba", "free_chat") == fast_model()


def test_long_message_uses_chat_model():
    text = "x" * 100
    assert pick_chat_model(text, "free_chat") == chat_model()


def test_setback_uses_chat_model():
    assert pick_chat_model("geriledim", "setback") == chat_model()


def test_complex_question_uses_chat_model():
    text = "Neden son günlerde motivasyonum düşük?"
    assert pick_chat_model(text, "free_chat") == chat_model()
