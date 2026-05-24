from app.ai.model_settings import chat_model, embedding_model, fast_model, vision_model
from app.config import Settings


def test_model_settings_defaults():
    settings = Settings()
    assert settings.openai_chat_model == "gpt-4o"
    assert settings.openai_fast_model == "gpt-4o-mini"
    assert settings.openai_vision_model == "gpt-4o"
    assert settings.openai_embedding_model == "text-embedding-3-small"


def test_model_settings_env_override(monkeypatch):
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-5.4")
    monkeypatch.setenv("OPENAI_FAST_MODEL", "gpt-5.4-mini")
    from app.config import Settings as S

    s = S()
    assert s.openai_chat_model == "gpt-5.4"
    assert s.openai_fast_model == "gpt-5.4-mini"


def test_model_settings_helpers(monkeypatch):
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "custom-chat")
    monkeypatch.setenv("OPENAI_FAST_MODEL", "custom-fast")
    get_settings = __import__("app.config", fromlist=["get_settings"]).get_settings
    get_settings.cache_clear()

    assert chat_model() == "custom-chat"
    assert fast_model() == "custom-fast"
    assert vision_model()  # has default
    assert embedding_model()  # has default

    get_settings.cache_clear()
