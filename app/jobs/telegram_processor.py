_bot = None
_dp = None


def get_worker_bot():
    global _bot
    if _bot is None:
        from app.bot.dispatcher import create_bot
        from app.config import get_settings

        if not get_settings().telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        _bot = create_bot()
    return _bot


def get_worker_dispatcher():
    global _dp
    if _dp is None:
        from app.bot.dispatcher import create_dispatcher

        _dp = create_dispatcher()
    return _dp


async def process_update(update_data: dict) -> None:
    from datetime import datetime, timezone

    import structlog
    from aiogram.types import Update

    from app.infra.redis import get_redis
    from app.metrics import ARQ_JOBS_FAILED

    logger = structlog.get_logger()
    update_id = update_data.get("update_id")
    structlog.contextvars.bind_contextvars(update_id=update_id)

    try:
        update = Update.model_validate(update_data)
        await get_worker_dispatcher().feed_update(get_worker_bot(), update)
        redis = await get_redis()
        await redis.set("worker:heartbeat", datetime.now(timezone.utc).isoformat(), ex=120)
        logger.info("telegram.update_processed", update_id=update_id)
    except Exception as exc:
        ARQ_JOBS_FAILED.labels(job="process_telegram_update").inc()
        logger.error("telegram.update_failed", update_id=update_id, error=str(exc))
        raise
