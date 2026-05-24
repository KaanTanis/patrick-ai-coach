from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    allowed_telegram_ids: list[int] = []
    openai_api_key: str = ""
    database_url: str = "postgresql+asyncpg://tbot:tbot@localhost:5432/tbot"
    redis_url: str = "redis://localhost:6379/0"
    api_key: str = "change-me"
    user_timezone: str = "Europe/Istanbul"
    checkin_nudge_hour: int = 8
    proactive_outreach_enabled: bool = True
    max_daily_nudges: int = 3
    min_hours_between_nudges: int = 3
    outreach_eval_interval_minutes: int = 30
    chat_session_ttl_minutes: int = 45
    webhook_base_url: str = "http://localhost:8000"
    photo_storage_path: Path = Path("./data/photos")
    prompt_version: str = "1"
    max_daily_vision_calls: int = 20
    daily_calorie_soft_limit: int = 2200
    max_meals_before_nudge: int = 4
    chat_history_token_budget: int = 2500
    memory_retrieval_limit: int = 15
    episodic_days: int = 30
    debug: bool = False

    @field_validator("allowed_telegram_ids", mode="before")
    @classmethod
    def parse_allowed_ids(cls, value: str | list[int]) -> list[int]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [int(item.strip()) for item in str(value).split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
