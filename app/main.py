from contextlib import asynccontextmanager

import structlog
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import insights, memories, metrics
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

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
    logger.info("app.starting")
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
        await _bot.session.close()
    logger.info("app.stopped")


app = FastAPI(title="tbot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(memories.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid secret")

    data = await request.json()
    update = Update.model_validate(data)
    await get_dispatcher().feed_update(get_bot(), update)
    return {"ok": True}


dashboard_dist = __import__("pathlib").Path(__file__).parent.parent / "dashboard" / "dist"
if dashboard_dist.exists():
    app.mount("/", StaticFiles(directory=dashboard_dist, html=True), name="dashboard")
