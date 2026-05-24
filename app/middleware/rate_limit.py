import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.infra.redis import get_redis


class ApiRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int = 120):
        super().__init__(app)
        self.limit_per_minute = limit_per_minute

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_key = request.headers.get("X-API-Key") or request.client.host if request.client else "anon"
        bucket = f"api_rl:{client_key}:{int(time.time()) // 60}"

        try:
            redis = await get_redis()
            count = await redis.incr(bucket)
            if count == 1:
                await redis.expire(bucket, 60)
            if count > self.limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again in a minute."},
                )
        except Exception:
            pass

        return await call_next(request)
