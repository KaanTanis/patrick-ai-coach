import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.prompt_composer import PromptComposer


@pytest.mark.asyncio
async def test_compose_includes_core_identity():
    session = AsyncMock()
    repo_mock = AsyncMock()
    repo_mock.get = AsyncMock(return_value=None)

    with patch.object(PromptComposer, "_get_personality_prompt", new=AsyncMock(return_value="Be warm.")):
        composer = PromptComposer(session)
        composer.personalities = repo_mock

        user = MagicMock()
        user.personality_key = "companion"
        user.goals = {"smoking": "quit"}
        user.timezone = "Europe/Istanbul"
        user.context_summary = None
        user.schedule = None

        messages = await composer.compose(
            user=user,
            user_message="Hello",
            memories=[],
            checkins=[],
            history=[],
        )

    assert messages[0]["role"] == "system"
    assert "Asla utandırma" in messages[0]["content"]
    assert messages[-1]["content"] == "Hello"
