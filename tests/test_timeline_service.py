import pytest
from unittest.mock import AsyncMock, patch

from app.services.timeline import TimelineService


@pytest.mark.asyncio
async def test_timeline_build_empty():
    session = AsyncMock()
    service = TimelineService(session)

    with patch.object(service.check_ins, "get_recent", AsyncMock(return_value=[])), \
         patch.object(service.meals, "get_recent", AsyncMock(return_value=[])), \
         patch.object(service.memories, "list_all", AsyncMock(return_value=[])), \
         patch.object(service.dreams, "get_recent", AsyncMock(return_value=[])), \
         patch.object(service.shadows, "get_recent", AsyncMock(return_value=[])), \
         patch.object(service.stoic, "get_recent", AsyncMock(return_value=[])), \
         patch.object(service.emotions, "get_recent", AsyncMock(return_value=[])):
        events = await service.build(1, days=7)

    assert events == []
