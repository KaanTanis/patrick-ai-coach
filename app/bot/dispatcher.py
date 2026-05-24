from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from app.bot.handlers import (
    cancel,
    chat,
    checkin,
    commands,
    food,
    insights,
    memory,
    menu_buttons,
    personality,
    relapse,
    start,
)
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.config import get_settings

settings = get_settings()


def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    dp.include_router(cancel.router)
    dp.include_router(start.router)
    dp.include_router(commands.router)
    dp.include_router(menu_buttons.router)
    dp.include_router(checkin.router)
    dp.include_router(personality.router)
    dp.include_router(insights.router)
    dp.include_router(relapse.router)
    dp.include_router(memory.router)
    dp.include_router(food.router)
    dp.include_router(chat.router)

    return dp


def create_bot() -> Bot:
    return Bot(token=settings.telegram_bot_token)
