import pytest
from unittest.mock import AsyncMock, patch

from app.services.lens import set_lens, get_lens, clear_lens, VALID_LENSES


@pytest.mark.asyncio
async def test_set_and_get_lens():
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.get = AsyncMock(return_value="jung")
    with patch("app.services.lens.get_redis", AsyncMock(return_value=redis)):
        await set_lens(123, "jung")
        redis.setex.assert_called_once()
        value = await get_lens(123)
        assert value == "jung"


@pytest.mark.asyncio
async def test_clear_lens():
    redis = AsyncMock()
    redis.delete = AsyncMock()
    with patch("app.services.lens.get_redis", AsyncMock(return_value=redis)):
        await clear_lens(123)
        redis.delete.assert_called_once()


def test_valid_lenses():
    assert "stoic" in VALID_LENSES
