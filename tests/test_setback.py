import pytest

from app.ai.behavioral.setback import SetbackRecovery, detect_setback_intent
from app.ai.interview.stop_phrases import is_stop_phrase


def test_detect_setback_intent_generic():
    assert detect_setback_intent("bugün geriledim") is True
    assert detect_setback_intent("bugün iyiydim") is False


def test_is_stop_phrase():
    assert is_stop_phrase("bu kadar soru yeter") is True
    assert is_stop_phrase("merhaba") is False


@pytest.mark.asyncio
async def test_setback_creates_memory():
    from unittest.mock import AsyncMock, patch

    session = AsyncMock()
    recovery = SetbackRecovery(session)
    recovery.memories.get_recent_relapse = AsyncMock(return_value=None)
    recovery.memories.create = AsyncMock()

    with patch("app.ai.behavioral.setback.get_openai_client") as client_cls:
        client_cls.return_value.chat = AsyncMock(return_value="Destek mesajı")
        result = await recovery.handle(1, "geriledim", "companion")

    recovery.memories.create.assert_awaited_once()
    assert "Destek" in result
