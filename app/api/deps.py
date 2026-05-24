import secrets

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session

settings = get_settings()


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


async def get_db_session() -> AsyncSession:
    async for session in get_session():
        yield session
