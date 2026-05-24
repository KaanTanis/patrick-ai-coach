import redis.asyncio as aioredis

from app.config import get_settings
from app.repositories import new_session_id

settings = get_settings()


def _key(telegram_id: int) -> str:
    return f"chat_session:{telegram_id}"


async def get_or_create_session_id(telegram_id: int) -> str:
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        existing = await client.get(_key(telegram_id))
        if existing:
            await client.expire(_key(telegram_id), settings.chat_session_ttl_minutes * 60)
            return existing
        session_id = new_session_id()
        await client.setex(_key(telegram_id), settings.chat_session_ttl_minutes * 60, session_id)
        return session_id
    finally:
        await client.aclose()


async def touch_session(telegram_id: int, session_id: str) -> None:
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.setex(_key(telegram_id), settings.chat_session_ttl_minutes * 60, session_id)
    finally:
        await client.aclose()


async def clear_session(telegram_id: int) -> None:
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.delete(_key(telegram_id))
    finally:
        await client.aclose()
