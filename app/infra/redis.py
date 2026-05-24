from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

_redis: aioredis.Redis | None = None
_arq_pool: ArqRedis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _arq_pool


async def enqueue_job(job_name: str, *args, **kwargs) -> None:
    pool = await get_arq_pool()
    await pool.enqueue_job(job_name, *args, **kwargs)


async def close_infra() -> None:
    global _redis, _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None
