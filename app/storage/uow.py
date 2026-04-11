"""Unit of Work implementation for transactional repository access."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.source_management.repository import SourceRepository
from app.storage.db.session import SessionFactory
from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
from app.storage.repositories.raw_item_repository import RawItemRepository
from app.storage.repositories.topic_repository import TopicRepository


class UnitOfWork:
    """Aggregate repositories and provide transaction boundary."""

    def __init__(self) -> None:
        self._session: AsyncSession | None = None
        self.sources: SourceRepository | None = None
        self.raw_items: RawItemRepository | None = None
        self.normalized_items: NormalizedItemRepository | None = None
        self.topics: TopicRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self._session = SessionFactory()
        self.sources = SourceRepository(self._session)
        self.raw_items = RawItemRepository(self._session)
        self.normalized_items = NormalizedItemRepository(self._session)
        self.topics = TopicRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        if self._session is None:
            return
        if exc:
            await self.rollback()
        else:
            await self.commit()
        await self._session.close()

    async def commit(self) -> None:
        """Commit current transaction."""
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        if self._session is not None:
            await self._session.rollback()
