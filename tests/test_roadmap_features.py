import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.behavioral.setback import detect_setback_intent
from app.repositories import InsightRepository


def test_detect_setback_intent():
    assert detect_setback_intent("bugün geriledim") is True
    assert detect_setback_intent("günaydın") is False


@pytest.mark.asyncio
async def test_insight_dismiss():
    session = AsyncMock()
    insight = MagicMock()
    insight.dismissed = False
    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=insight)
    session.execute = AsyncMock(return_value=result_mock)

    repo = InsightRepository(session)
    ok = await repo.dismiss(1, 10)
    assert ok is True
    assert insight.dismissed is True


@pytest.mark.asyncio
async def test_setback_fsm_states_exist():
    from app.bot.states import SetbackStates

    assert SetbackStates.description
    assert SetbackStates.trigger
    assert SetbackStates.action
