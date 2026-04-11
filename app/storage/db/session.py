"""Database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.bootstrap.settings import get_settings
from app.common.exceptions import InfrastructureError

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database.url,
    echo=settings.app.debug,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async with SessionFactory() as session:
        yield session


async def ping_database() -> None:
    """Check database connectivity.

    Raises:
        InfrastructureError: If database is unreachable.
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise InfrastructureError(f"Database ping failed: {exc}") from exc
