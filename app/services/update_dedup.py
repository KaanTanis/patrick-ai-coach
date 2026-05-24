from app.infra.redis import get_redis

UPDATE_KEY_PREFIX = "telegram:update:"
UPDATE_TTL_SECONDS = 86400


async def try_claim_update(update_id: int) -> bool:
    redis = await get_redis()
    key = f"{UPDATE_KEY_PREFIX}{update_id}"
    return bool(await redis.set(key, "1", nx=True, ex=UPDATE_TTL_SECONDS))
