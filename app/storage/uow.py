"""Unit of Work implementation for transactional repository access."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.repositories.entity_memory_repository import EntityMemoryRepository
from app.memory.repositories.judgement_repository import JudgementRepository
from app.memory.repositories.timeline_repository import TimelineRepository
from app.memory.repositories.topic_memory_repository import TopicMemoryRepository
from app.source_management.repository import SourceRepository
from app.storage.db.session import SessionFactory
from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
from app.storage.repositories.raw_item_repository import RawItemRepository
from app.storage.repositories.report_repository import ReportRepository
from app.storage.repositories.topic_repository import TopicRepository


class UnitOfWork:
    """Aggregate repositories and provide transaction boundary."""

    def __init__(self) -> None:
        self._session: AsyncSession | None = None
        self.sources: SourceRepository | None = None
        self.raw_items: RawItemRepository | None = None
        self.normalized_items: NormalizedItemRepository | None = None
        self.topics: TopicRepository | None = None
        self.reports: ReportRepository | None = None
        # Memory repositories
        self.topic_memories: TopicMemoryRepository | None = None
        self.entity_memories: EntityMemoryRepository | None = None
        self.judgements: JudgementRepository | None = None
        self.timelines: TimelineRepository | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self._session = SessionFactory()
        self.sources = SourceRepository(self._session)
        self.raw_items = RawItemRepository(self._session)
        self.normalized_items = NormalizedItemRepository(self._session)
        self.topics = TopicRepository(self._session)
        self.reports = ReportRepository(self._session)
        # Memory repositories
        self.topic_memories = TopicMemoryRepository(self._session)
        self.entity_memories = EntityMemoryRepository(self._session)
        self.judgements = JudgementRepository(self._session)
        self.timelines = TimelineRepository(self._session)
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

    @property
    def session(self) -> AsyncSession | None:
        """Get the current session."""
        return self._session
