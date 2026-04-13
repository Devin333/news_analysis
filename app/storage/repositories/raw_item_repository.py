"""RawItem repository implementation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.raw_item import RawItemDTO
from app.storage.db.models.raw_item import RawItem

logger = get_logger(__name__)


def _to_dto(item: RawItem) -> RawItemDTO:
    """Convert ORM model to RawItemDTO."""
    return RawItemDTO(
        id=item.id,
        source_id=item.source_id,
        external_id=item.external_id,
        url=item.url,
        canonical_url=item.canonical_url,
        raw_html=item.raw_html,
        raw_json=item.raw_json,
        raw_text=item.raw_text,
        fetched_at=item.fetched_at,
        checksum=item.checksum,
        parse_status=item.parse_status,
    )


class RawItemRepository:
    """RawItem repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: RawItemDTO) -> RawItemDTO:
        """Create a raw item."""
        item = RawItem(
            source_id=data.source_id,
            external_id=data.external_id,
            url=data.url,
            canonical_url=data.canonical_url,
            raw_html=data.raw_html,
            raw_json=data.raw_json,
            raw_text=data.raw_text,
            fetched_at=data.fetched_at,
            checksum=data.checksum,
            parse_status=data.parse_status,
        )
        self._session.add(item)
        await self._session.flush()
        return _to_dto(item)

    async def bulk_create(self, items: list[RawItemDTO]) -> list[RawItemDTO]:
        """Bulk create raw items."""
        created: list[RawItemDTO] = []
        for data in items:
            item = RawItem(
                source_id=data.source_id,
                external_id=data.external_id,
                url=data.url,
                canonical_url=data.canonical_url,
                raw_html=data.raw_html,
                raw_json=data.raw_json,
                raw_text=data.raw_text,
                fetched_at=data.fetched_at,
                checksum=data.checksum,
                parse_status=data.parse_status,
            )
            self._session.add(item)
            created.append(data)
        await self._session.flush()
        logger.info(f"Bulk created {len(created)} raw items")
        return created

    async def get_by_url(self, url: str) -> RawItemDTO | None:
        """Get raw item by URL."""
        result = await self._session.execute(
            select(RawItem).where(RawItem.url == url)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        return _to_dto(item)

    async def list_by_source(
        self, source_id: int, *, limit: int = 100
    ) -> list[RawItemDTO]:
        """List raw items by source."""
        result = await self._session.execute(
            select(RawItem)
            .where(RawItem.source_id == source_id)
            .order_by(RawItem.fetched_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [_to_dto(i) for i in items]

    async def exists_by_checksum(self, checksum: str) -> bool:
        """Check if item exists by checksum."""
        result = await self._session.execute(
            select(func.count()).select_from(RawItem).where(RawItem.checksum == checksum)
        )
        count = result.scalar_one()
        return count > 0

    async def list_pending(self, *, limit: int = 200) -> list[RawItemDTO]:
        """List raw items with parse_status='pending'."""
        result = await self._session.execute(
            select(RawItem)
            .where(RawItem.parse_status == "pending")
            .order_by(RawItem.fetched_at.asc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [_to_dto(i) for i in items]

    async def update_parse_status(self, item_id: int, status: str) -> bool:
        """Update parse_status for a raw item."""
        from sqlalchemy import update
        result = await self._session.execute(
            update(RawItem)
            .where(RawItem.id == item_id)
            .values(parse_status=status)
        )
        await self._session.flush()
        return getattr(result, "rowcount", 0) > 0
