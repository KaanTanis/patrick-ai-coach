import asyncio
import base64
from functools import lru_cache
from pathlib import Path
from typing import Any

import structlog
import tiktoken
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings

logger = structlog.get_logger()


class OpenAIClient:
    def __init__(self, api_key: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key or "not-set")
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> str:
        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                logger.warning("openai.chat_retry", attempt=attempt, error=str(exc))
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        return ""

    async def chat_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
        model: str = "gpt-4o-mini",
    ) -> BaseModel:
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
                return parsed
            except Exception as exc:
                logger.warning("openai.structured_retry", attempt=attempt, error=str(exc))
                if attempt == 2:
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("Structured chat failed")

    async def embed(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        response = await self.client.embeddings.create(model=model, input=text)
        return response.data[0].embedding

    async def analyze_food_image(self, image_path: Path, prompt: str) -> str:
        image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        suffix = image_path.suffix.lower().lstrip(".")
        mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix or "jpeg"

        response = await self.client.chat.completions.create(
            model="gpt-4o",
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
        return response.choices[0].message.content or ""


@lru_cache
def get_openai_client() -> OpenAIClient:
    return OpenAIClient(get_settings().openai_api_key)
