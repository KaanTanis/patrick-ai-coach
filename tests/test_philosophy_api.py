import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("ENV", "development")

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def test_philosophy_emotions_requires_key():
    response = client.get("/api/philosophy/emotions")
    assert response.status_code == 422


def test_philosophy_emotions_invalid_key():
    response = client.get("/api/philosophy/emotions", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_philosophy_emotions_no_user():
    with patch("app.api.routes.philosophy.get_primary_user", AsyncMock(return_value=None)):
        response = client.get(
            "/api/philosophy/emotions",
            headers={"X-API-Key": settings.api_key},
        )
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_philosophy_stoic_streak():
    user = MagicMock(id=1)
    with (
        patch("app.api.routes.philosophy.get_primary_user", AsyncMock(return_value=user)),
        patch("app.api.routes.philosophy.StoicRitualRepository") as repo_cls,
    ):
        repo_cls.return_value.count_recent_by_type = AsyncMock(
            return_value={"morning": 4, "evening": 3}
        )
        response = client.get(
            "/api/philosophy/stoic/streak?days=30",
            headers={"X-API-Key": settings.api_key},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["morning"] == 4
    assert body["evening"] == 3
    assert body["total"] == 7
