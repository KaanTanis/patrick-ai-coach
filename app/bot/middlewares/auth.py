from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not settings.allowed_telegram_ids:
            if settings.is_production:
                logger.error("auth.production_no_allowlist")
                if isinstance(event, Message):
                    await event.answer("Bot yapılandırması hatalı. Yöneticiye bildir.")
                return None
            logger.warning("auth.no_allowlist_configured")
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id not in settings.allowed_telegram_ids:
            logger.info("auth.rejected", user_id=user.id)
            if isinstance(event, Message):
                await event.answer("Bu bot özel. Erişim reddedildi.")
            return None

        return await handler(event, data)
