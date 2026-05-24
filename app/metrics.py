import time
from collections.abc import Callable

from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

WEBHOOK_DURATION = Histogram(
    "tbot_webhook_duration_seconds",
    "Telegram webhook request duration",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
OPENAI_REQUESTS = Counter(
    "tbot_openai_requests_total",
    "OpenAI API requests",
    ["model", "operation", "status"],
)
OPENAI_TOKENS = Counter(
    "tbot_openai_tokens_total",
    "OpenAI tokens used",
    ["model", "direction"],
)
ARQ_JOBS_FAILED = Counter(
    "tbot_arq_jobs_failed_total",
    "Failed ARQ background jobs",
    ["job"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path != "/webhook/telegram":
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        WEBHOOK_DURATION.observe(time.perf_counter() - start)
        return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4")
