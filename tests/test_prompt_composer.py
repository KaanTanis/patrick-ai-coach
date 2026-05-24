import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.prompt_composer import PromptComposer


@pytest.mark.asyncio
async def test_compose_includes_core_identity():
    session = AsyncMock()
    profile = MagicMock()
    profile.system_prompt = "Be warm."
    profile.tone_rules = {"voice": "calm"}

    with patch.object(PromptComposer, "_get_personality", new=AsyncMock(return_value=profile)):
        composer = PromptComposer(session)

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
