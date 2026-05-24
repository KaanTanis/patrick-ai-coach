from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


DEFAULT_PREFERENCES: dict[str, Any] = {
    "free_mode": False,
    "proactive_nudges": True,
    "onboarding_complete": False,
}


class PreferencesService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int) -> dict[str, Any]:
        user = await self.session.get(User, user_id)
        if not user:
            return dict(DEFAULT_PREFERENCES)
        prefs = user.preferences or {}
        return {**DEFAULT_PREFERENCES, **prefs}

    async def update(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        current = await self.get(user_id)
        current.update(updates)
        await self.session.execute(
            update(User).where(User.id == user_id).values(preferences=current)
        )
        return current

    async def is_free_mode(self, user_id: int) -> bool:
        return bool((await self.get(user_id)).get("free_mode"))

    async def proactive_enabled(self, user_id: int) -> bool:
        prefs = await self.get(user_id)
        if prefs.get("free_mode"):
            return False
        return bool(prefs.get("proactive_nudges", True))
