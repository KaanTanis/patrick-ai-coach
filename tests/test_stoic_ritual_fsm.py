from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers.stoic_ritual import (
    finish_morning,
    process_m_control,
    skip_m_control,
)
from app.bot.states import StoicMorningStates


@pytest.mark.asyncio
async def test_process_m_control_splits_items():
    message = MagicMock()
    message.text = "nefes, odak, sabır"
    message.answer = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    await process_m_control(message, state)

    state.update_data.assert_awaited_once_with(
        control_items=["nefes", "odak", "sabır"]
    )
    state.set_state.assert_awaited_with(StoicMorningStates.premeditatio)


@pytest.mark.asyncio
async def test_skip_m_control_moves_to_premeditatio():
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    await skip_m_control(callback, state)

    state.update_data.assert_awaited_with(control_items=[])
    state.set_state.assert_awaited_with(StoicMorningStates.premeditatio)


@pytest.mark.asyncio
async def test_finish_morning_persists_ritual():
    message = MagicMock()
    message.text = "Bugün sabırlı olacağım"
    message.from_user = MagicMock(id=123, full_name="Test")
    message.answer = AsyncMock()
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={"control_items": ["odak"], "premeditatio": "toplantı"}
    )
    state.clear = AsyncMock()
    session = AsyncMock()
    user = MagicMock(id=1)

    with (
        patch("app.bot.handlers.stoic_ritual.UserRepository") as users_cls,
        patch("app.bot.handlers.stoic_ritual.StoicRitualRepository") as repo_cls,
    ):
        users_cls.return_value.get_or_create = AsyncMock(return_value=user)
        repo_cls.return_value.create = AsyncMock()
        await finish_morning(message, state, session)

    repo_cls.return_value.create.assert_awaited_once()
    create_data = repo_cls.return_value.create.call_args[0][1]
    assert create_data["ritual_type"] == "morning"
    assert create_data["virtue_intention"] == "Bugün sabırlı olacağım"
