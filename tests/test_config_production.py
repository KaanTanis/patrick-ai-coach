import pytest

from app.config import Settings


def test_production_validation_passes():
    settings = Settings(
        env="production",
        telegram_bot_token="token",
        openai_api_key="key",
        allowed_telegram_ids=[123],
        telegram_webhook_secret="secret",
        api_key="secure-key",
    )
    settings.validate_production()


def test_production_validation_fails_without_allowlist():
    settings = Settings.model_construct(
        env="production",
        telegram_bot_token="token",
        openai_api_key="key",
        telegram_webhook_secret="secret",
        api_key="secure-key",
        allowed_telegram_ids=[],
    )
    with pytest.raises(RuntimeError, match="ALLOWED_TELEGRAM_IDS"):
        settings.validate_production()


def test_development_skips_validation():
    settings = Settings(env="development", api_key="change-me")
    settings.validate_production()
