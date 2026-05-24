from contextlib import asynccontextmanager

import structlog
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes import insights, memories, metrics, philosophy, timeline
from app.config import get_settings
from app.db import async_session_factory, engine
from app.infra.redis import close_infra, get_redis
from app.logging_config import configure_logging
from app.metrics import MetricsMiddleware, metrics_response
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.rate_limit import ApiRateLimitMiddleware

configure_logging()
logger = structlog.get_logger()
settings = get_settings()

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

_bot = None
_dp = None


def get_bot():
    global _bot
    if _bot is None:
        from app.bot.dispatcher import create_bot

        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        _bot = create_bot()
    return _bot


def get_dispatcher():
    global _dp
    if _dp is None:
        from app.bot.dispatcher import create_dispatcher

        _dp = create_dispatcher()
    return _dp


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production()
    logger.info("app.starting", env=settings.env)

    if settings.telegram_bot_token:
        bot = get_bot()
        from app.bot.commands_registry import BOT_COMMANDS

        await bot.set_my_commands(BOT_COMMANDS)
        if settings.webhook_base_url:
            webhook_url = f"{settings.webhook_base_url.rstrip('/')}/webhook/telegram"
            await bot.set_webhook(
                url=webhook_url,
                secret_token=settings.telegram_webhook_secret or None,
            )
            logger.info("webhook.set", url=webhook_url)

    yield

    if _bot is not None:
        if settings.webhook_base_url:
            await _bot.delete_webhook(drop_pending_updates=False)
        await _bot.session.close()
    await close_infra()
    await engine.dispose()
    logger.info("app.stopped")


app = FastAPI(title="tbot", lifespan=lifespan)

cors_origins = [settings.dashboard_origin] if settings.is_production else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.is_production,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(ApiRateLimitMiddleware)
app.add_middleware(MetricsMiddleware)

app.include_router(metrics.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(memories.router, prefix="/api")
app.include_router(philosophy.router, prefix="/api")
app.include_router(timeline.router, prefix="/api")


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = str(exc)
        healthy = False

    try:
        redis = await get_redis()
        pong = await redis.ping()
        checks["redis"] = "ok" if pong else "fail"
        if not pong:
            healthy = False
    except Exception as exc:
        checks["redis"] = str(exc)
        healthy = False

    try:
        redis = await get_redis()
        heartbeat = await redis.get("worker:heartbeat")
        checks["worker"] = "ok" if heartbeat else "stale"
    except Exception as exc:
        checks["worker"] = str(exc)

    status_code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


@app.get("/health")
async def health():
    return await health_ready()


@app.get("/metrics")
async def prometheus_metrics():
    return metrics_response()


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")

    data = await request.json()
    update_id = data.get("update_id")
    structlog.contextvars.bind_contextvars(update_id=update_id)

    if settings.async_webhook:
        from app.services.update_dedup import try_claim_update
        from app.infra.redis import enqueue_job

        if update_id is not None and not await try_claim_update(update_id):
            logger.info("webhook.deduplicated", update_id=update_id)
            return {"ok": True, "deduplicated": True}

        await enqueue_job("process_telegram_update_task", data)
        return {"ok": True}

    update = Update.model_validate(data)
    await get_dispatcher().feed_update(get_bot(), update)
    return {"ok": True}


dashboard_dist = __import__("pathlib").Path(__file__).parent.parent / "dashboard" / "dist"
if dashboard_dist.exists():
    app.mount("/", StaticFiles(directory=dashboard_dist, html=True), name="dashboard")
