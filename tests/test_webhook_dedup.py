from unittest.mock import AsyncMock, patch

import pytest

from app.services.update_dedup import try_claim_update


@pytest.mark.asyncio
async def test_try_claim_update_first_time():
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    with patch("app.services.update_dedup.get_redis", return_value=mock_redis):
        assert await try_claim_update(42) is True
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_try_claim_update_duplicate():
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False
    with patch("app.services.update_dedup.get_redis", return_value=mock_redis):
        assert await try_claim_update(42) is False
