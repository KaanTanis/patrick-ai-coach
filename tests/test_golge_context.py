from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers.philosophy_core import cmd_shadow
from app.bot.handlers.psych import THERAPY_DISCLAIMER, _crisis_in, tr_situation


def test_crisis_in_detects_keyword():
    assert _crisis_in("intihar düşüncelerim var") is True
    assert _crisis_in("bugün yorgunum") is False


@pytest.mark.asyncio
async def test_tr_situation_crisis_response():
    message = MagicMock()
    message.text = "ölmek istiyorum"
    message.answer = AsyncMock()
    state = AsyncMock()
    state.clear = AsyncMock()

    await tr_situation(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    response_text = message.answer.call_args[0][0]
    assert "182" in response_text or "112" in response_text


def test_therapy_disclaimer_text():
    assert "terapi seansı değil" in THERAPY_DISCLAIMER


@pytest.mark.asyncio
async def test_cmd_shadow_includes_context_in_prompt():
    message = MagicMock()
    message.text = "/golge patrona sinirlendim"
    message.from_user = MagicMock(id=123, full_name="Test")
    message.answer = AsyncMock()

    session = AsyncMock()
    user = MagicMock(id=1)
    checkin = MagicMock(date=date(2026, 5, 20), mood=5, stress=8)

    with (
        patch("app.bot.handlers.philosophy_core.UserRepository") as users_cls,
        patch("app.bot.handlers.philosophy_core.CheckInRepository") as checkins_cls,
        patch("app.bot.handlers.philosophy_core.MemoryRepository") as memories_cls,
        patch("app.bot.handlers.philosophy_core.ShadowRepository") as shadows_cls,
        patch("app.bot.handlers.philosophy_core.get_openai_client") as client_cls,
    ):
        users_cls.return_value.get_or_create = AsyncMock(return_value=user)
        checkins_cls.return_value.get_recent = AsyncMock(return_value=[checkin])
        memories_cls.return_value.get_recent_relapse = AsyncMock(return_value=None)
        shadows_cls.return_value.get_recent = AsyncMock(return_value=[])
        shadows_cls.return_value.create = AsyncMock()
        client_cls.return_value.chat = AsyncMock(return_value="Yansıtma")

        await cmd_shadow(message, session)

    prompt = client_cls.return_value.chat.call_args[0][0][0]["content"]
    assert "ruh_hali=5" in prompt
    assert "patrona sinirlendim" in prompt
