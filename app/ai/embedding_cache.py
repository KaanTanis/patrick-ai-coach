import hashlib
import json

from app.infra.redis import get_redis

EMBED_PREFIX = "embed:"
EMBED_TTL = 86400 * 7


async def get_cached_embedding(text: str) -> list[float] | None:
    key = EMBED_PREFIX + hashlib.sha256(text.encode()).hexdigest()
    redis = await get_redis()
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_embedding(text: str, embedding: list[float]) -> None:
    key = EMBED_PREFIX + hashlib.sha256(text.encode()).hexdigest()
    redis = await get_redis()
    await redis.setex(key, EMBED_TTL, json.dumps(embedding))
