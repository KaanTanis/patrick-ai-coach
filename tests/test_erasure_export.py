import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.export import ErasureService, ExportService


@pytest.mark.asyncio
async def test_export_includes_checksum_and_profile():
    session = AsyncMock()
    user = MagicMock()
    user.telegram_id = 1
    user.name = "Test"
    user.personality_key = "companion"
    user.goals = {}
    user.timezone = "Europe/Istanbul"
    user.context_summary = "Özet"
    user.schedule = {"sleep_window": "23:00-07:00"}
    session.get = AsyncMock(return_value=user)

    service = ExportService(session)
    empty = AsyncMock(return_value=[])

    with (
        patch("app.services.export.CheckInRepository") as ci,
        patch("app.services.export.MealRepository") as meal,
        patch("app.services.export.SmokingEventRepository") as smoke,
        patch("app.services.export.WorkoutRepository") as workout,
        patch("app.services.export.ConversationRepository") as conv,
        patch("app.services.export.MemoryRepository") as mem,
        patch("app.services.export.InsightRepository") as ins,
        patch("app.services.export.DreamRepository") as dream,
        patch("app.services.export.ShadowRepository") as shadow,
        patch("app.services.export.ThoughtRepository") as thought,
        patch("app.services.export.StoicRitualRepository") as stoic,
        patch("app.services.export.EmotionRepository") as emotion,
    ):
        ci.return_value.get_recent = empty
        meal.return_value.get_recent = empty
        smoke.return_value.get_recent = empty
        workout.return_value.get_recent = empty
        conv.return_value.get_recent = empty
        mem.return_value.list_all = empty
        ins.return_value.get_active = empty
        dream.return_value.get_recent = empty
        shadow.return_value.get_recent = empty
        thought.return_value.get_recent = empty
        stoic.return_value.get_recent = empty
        emotion.return_value.get_recent = empty

        payload = await service.export_all(1)

    assert "checksum_sha256" in payload
    assert payload["user"]["context_summary"] == "Özet"
    assert payload["user"]["schedule"]["sleep_window"] == "23:00-07:00"
    raw = json.dumps({k: v for k, v in payload.items() if k != "checksum_sha256"}, sort_keys=True, default=str)
    assert payload["checksum_sha256"] == hashlib.sha256(raw.encode()).hexdigest()


@pytest.mark.asyncio
async def test_erasure_deletes_user():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    meal = MagicMock()
    meal.photo_path = None
    service = ErasureService(session)
    with patch.object(service.meals, "get_recent", AsyncMock(return_value=[meal])):
        with patch("app.services.export.clear_session", AsyncMock()):
            counts = await service.erase_all(1, 123)
    assert counts["users"] == 1
