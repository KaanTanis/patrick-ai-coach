from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import UserRepository

settings = get_settings()


async def get_primary_user(session: AsyncSession, users: UserRepository | None = None):
    users = users or UserRepository(session)
    if settings.allowed_telegram_ids:
        user = await users.get_by_telegram_id(settings.allowed_telegram_ids[0])
        if user:
            return user
    from sqlalchemy import select

    from app.models import User

    result = await session.execute(select(User).order_by(User.id.asc()).limit(1))
    return result.scalar_one_or_none()
