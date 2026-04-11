"""Source repository implementation."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.source import SourceCreate, SourceRead, SourceUpdate
from app.source_management.models import Source

logger = get_logger(__name__)


def _to_read(source: Source) -> SourceRead:
    """Convert ORM model to SourceRead DTO."""
    return SourceRead(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        base_url=source.base_url,
        feed_url=source.feed_url,
        priority=source.priority,
        trust_score=float(source.trust_score),
        fetch_interval_minutes=source.fetch_interval_minutes,
        is_active=source.is_active,
        metadata_json=source.metadata_json,
    )


class SourceRepository:
    """Source repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: SourceCreate) -> SourceRead:
        """Create a new source."""
        source = Source(
            name=data.name,
            source_type=data.source_type,
            base_url=data.base_url,
            feed_url=data.feed_url,
            priority=data.priority,
            trust_score=data.trust_score,
            fetch_interval_minutes=data.fetch_interval_minutes,
            is_active=data.is_active,
            metadata_json=data.metadata_json,
        )
        self._session.add(source)
        await self._session.flush()
        logger.info(f"Created source: {source.name} (id={source.id})")
        return _to_read(source)

    async def get_by_id(self, source_id: int) -> SourceRead | None:
        """Get source by ID."""
        result = await self._session.execute(
            select(Source).where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()
        if source is None:
            return None
        return _to_read(source)

    async def list_all(self, *, active_only: bool = False) -> list[SourceRead]:
        """List all sources."""
        stmt = select(Source).order_by(Source.priority.asc(), Source.id.asc())
        if active_only:
            stmt = stmt.where(Source.is_active.is_(True))
        result = await self._session.execute(stmt)
        sources = result.scalars().all()
        return [_to_read(s) for s in sources]

    async def update(self, source_id: int, data: SourceUpdate) -> SourceRead | None:
        """Update a source."""
        result = await self._session.execute(
            select(Source).where(Source.id == source_id)
        )
        source = result.scalar_one_or_none()
        if source is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(source, field, value)

        await self._session.flush()
        logger.info(f"Updated source id={source_id}")
        return _to_read(source)

    async def enable(self, source_id: int) -> bool:
        """Enable a source."""
        result = await self._session.execute(
            update(Source).where(Source.id == source_id).values(is_active=True)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def disable(self, source_id: int) -> bool:
        """Disable a source."""
        result = await self._session.execute(
            update(Source).where(Source.id == source_id).values(is_active=False)
        )
        await self._session.flush()
        return result.rowcount > 0
