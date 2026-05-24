import asyncio
import base64
import time
from functools import lru_cache
from pathlib import Path

import structlog
import tiktoken
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.ai.embedding_cache import get_cached_embedding, set_cached_embedding
from app.config import get_settings
from app.metrics import OPENAI_REQUESTS, OPENAI_TOKENS

logger = structlog.get_logger()
settings = get_settings()

CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_OPEN_SECONDS = 60


class CircuitOpenError(RuntimeError):
    pass


class _CircuitBreaker:
    def __init__(self) -> None:
        self.failure_count = 0
        self.open_until = 0.0

    def is_open(self) -> bool:
        now = time.time()
        if now < self.open_until:
            return True
        if self.open_until > 0 and now >= self.open_until:
            self.failure_count = 0
            self.open_until = 0.0
        return False

    def record_success(self) -> None:
        self.failure_count = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= CIRCUIT_FAILURE_THRESHOLD:
            self.open_until = time.time() + CIRCUIT_OPEN_SECONDS
            logger.warning("openai.circuit_open", seconds=CIRCUIT_OPEN_SECONDS)


_circuit = _CircuitBreaker()
CIRCUIT_OPEN_MESSAGE = "Şu an yanıt veremiyorum — biraz sonra tekrar dene."


class OpenAIClient:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key or "not-set")
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _check_circuit(self) -> None:
        if _circuit.is_open():
            raise CircuitOpenError(CIRCUIT_OPEN_MESSAGE)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> str:
        self._check_circuit()
        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = response.choices[0].message.content or ""
                usage = response.usage
                if usage:
                    OPENAI_TOKENS.labels(model=model, direction="prompt").inc(usage.prompt_tokens)
                    OPENAI_TOKENS.labels(model=model, direction="completion").inc(
                        usage.completion_tokens
                    )
                OPENAI_REQUESTS.labels(model=model, operation="chat", status="ok").inc()
                _circuit.record_success()
                return text
            except CircuitOpenError:
                raise
            except Exception as exc:
                logger.warning("openai.chat_retry", attempt=attempt, error=str(exc))
                if attempt == 2:
                    OPENAI_REQUESTS.labels(model=model, operation="chat", status="error").inc()
                    _circuit.record_failure()
                    raise
                await asyncio.sleep(2**attempt)
        return ""

    async def chat_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        model: str = "gpt-4o-mini",
    ) -> BaseModel:
        self._check_circuit()
        for attempt in range(3):
            try:
                response = await self.client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_model,
                )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("Empty structured response")
                OPENAI_REQUESTS.labels(model=model, operation="structured", status="ok").inc()
                _circuit.record_success()
                return parsed
            except CircuitOpenError:
                raise
            except Exception as exc:
                logger.warning("openai.structured_retry", attempt=attempt, error=str(exc))
                if attempt == 2:
                    OPENAI_REQUESTS.labels(model=model, operation="structured", status="error").inc()
                    _circuit.record_failure()
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("Structured chat failed")

    async def embed(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        cached = await get_cached_embedding(text)
        if cached is not None:
            OPENAI_REQUESTS.labels(model=model, operation="embed", status="cache_hit").inc()
            return cached

        self._check_circuit()
        try:
            response = await self.client.embeddings.create(model=model, input=text)
            embedding = response.data[0].embedding
            await set_cached_embedding(text, embedding)
            OPENAI_REQUESTS.labels(model=model, operation="embed", status="ok").inc()
            _circuit.record_success()
            return embedding
        except Exception:
            OPENAI_REQUESTS.labels(model=model, operation="embed", status="error").inc()
            _circuit.record_failure()
            raise

    async def analyze_food_image(self, image_path: Path, prompt: str) -> str:
        self._check_circuit()
        image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        suffix = image_path.suffix.lower().lstrip(".")
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix or "jpeg"
        model = "gpt-4o"

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/{mime};base64,{image_data}"},
                            },
                        ],
                    }
                ],
                max_tokens=800,
            )
            OPENAI_REQUESTS.labels(model=model, operation="vision", status="ok").inc()
            _circuit.record_success()
            return response.choices[0].message.content or ""
        except Exception:
            OPENAI_REQUESTS.labels(model=model, operation="vision", status="error").inc()
            _circuit.record_failure()
            raise


@lru_cache
def get_openai_client() -> OpenAIClient:
    return OpenAIClient(get_settings().openai_api_key)
