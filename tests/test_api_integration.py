import os
from unittest.mock import AsyncMock, MagicMock, patch


os.environ.setdefault("ENV", "development")
os.environ.setdefault("ASYNC_WEBHOOK", "false")

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_with_mocks():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = "2026-01-01T00:00:00+00:00"

    session = AsyncMock()
    session.execute = AsyncMock()

    class FactoryCtx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return None

    with patch("app.main.get_redis", AsyncMock(return_value=mock_redis)):
        with patch("app.main.async_session_factory", return_value=FactoryCtx()):
            response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["postgres"] == "ok"


def test_api_metrics_requires_key():
    response = client.get("/api/metrics/checkins")
    assert response.status_code == 422


def test_api_metrics_invalid_key():
    response = client.get("/api/metrics/checkins", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_webhook_rejects_bad_secret_when_configured():
    with patch.object(settings, "telegram_webhook_secret", "expected"):
        response = client.post("/webhook/telegram", json={"update_id": 1})
    assert response.status_code == 403


def test_webhook_accepts_update_when_sync_mode():
    dispatcher = AsyncMock()
    with patch.object(settings, "telegram_webhook_secret", ""):
        with patch.object(settings, "async_webhook", False):
            with patch("app.main.get_dispatcher", return_value=dispatcher):
                with patch("app.main.get_bot", return_value=MagicMock()):
                    with patch("app.main.Update") as update_cls:
                        update_cls.model_validate.return_value = MagicMock()
                        response = client.post(
                            "/webhook/telegram",
                            json={"update_id": 99},
                        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    dispatcher.feed_update.assert_awaited_once()
