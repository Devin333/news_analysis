"""FastAPI dependency providers."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.settings import Settings, get_settings
from app.storage.db.session import SessionFactory


def get_app_settings() -> Settings:
    """Provide shared application settings."""
    return get_settings()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide database session dependency."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
