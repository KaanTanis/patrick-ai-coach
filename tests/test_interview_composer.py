import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.interview.composer import InterviewComposer, STEP_POOL
from app.ai.interview.stop_phrases import is_stop_phrase


@pytest.mark.asyncio
async def test_plan_steps_returns_subset():
    session = AsyncMock()
    composer = InterviewComposer(session)
    composer.users.get_by_id = AsyncMock(return_value=MagicMock(schedule={}))
    composer.check_ins.get_recent = AsyncMock(return_value=[])
    composer.memories.get_goals = AsyncMock(return_value=[])

    steps = await composer.plan_steps(1)
    assert 3 <= len(steps) <= 6
    assert "notes" in steps
    assert "cravings" not in steps and "mood" in STEP_POOL


@pytest.mark.asyncio
async def test_phrase_question_fallback():
    session = AsyncMock()
    composer = InterviewComposer(session)
    with patch("app.ai.interview.composer.get_openai_client") as client_cls:
        client_cls.return_value.chat = AsyncMock(side_effect=RuntimeError("fail"))
        text = await composer.phrase_question("mood", {}, 0, 5)
    assert "ruh hali" in text.lower() or "1-10" in text


def test_stop_phrase_variants():
    assert is_stop_phrase("Tamam bu kadar")
    assert is_stop_phrase("yeter bu kadar sorular")
