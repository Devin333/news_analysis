"""NormalizedItem repository implementation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.storage.db.models.normalized_item import NormalizedItem

logger = get_logger(__name__)


def _to_dto(item: NormalizedItem) -> NormalizedItemDTO:
    """Convert ORM model to NormalizedItemDTO."""
    return NormalizedItemDTO(
        id=item.id,
        raw_item_id=item.raw_item_id,
        source_id=item.source_id,
        title=item.title,
        clean_text=item.clean_text,
        excerpt=item.excerpt,
        author=item.author,
        published_at=item.published_at,
        language=item.language,
        content_type=item.content_type,
        board_type_candidate=item.board_type_candidate,
        quality_score=float(item.quality_score),
        ai_relevance_score=float(item.ai_relevance_score),
        canonical_url=item.canonical_url,
        metadata_json=item.metadata_json,
    )


class NormalizedItemRepository:
    """NormalizedItem repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: NormalizedItemDTO) -> NormalizedItemDTO:
        """Create a normalized item."""
        item = NormalizedItem(
            raw_item_id=data.raw_item_id,
            source_id=data.source_id,
            title=data.title,
            clean_text=data.clean_text,
            excerpt=data.excerpt,
            author=data.author,
            published_at=data.published_at,
            language=data.language,
            content_type=data.content_type,
            board_type_candidate=data.board_type_candidate,
            quality_score=data.quality_score,
            ai_relevance_score=data.ai_relevance_score,
            canonical_url=data.canonical_url,
            metadata_json=data.metadata_json,
        )
        self._session.add(item)
        await self._session.flush()
        return _to_dto(item)

    async def bulk_create(self, items: list[NormalizedItemDTO]) -> list[NormalizedItemDTO]:
        """Bulk create normalized items."""
        created: list[NormalizedItemDTO] = []
        for data in items:
            item = NormalizedItem(
                raw_item_id=data.raw_item_id,
                source_id=data.source_id,
                title=data.title,
                clean_text=data.clean_text,
                excerpt=data.excerpt,
                author=data.author,
                published_at=data.published_at,
                language=data.language,
                content_type=data.content_type,
                board_type_candidate=data.board_type_candidate,
                quality_score=data.quality_score,
                ai_relevance_score=data.ai_relevance_score,
                canonical_url=data.canonical_url,
                metadata_json=data.metadata_json,
            )
            self._session.add(item)
            created.append(data)
        await self._session.flush()
        logger.info(f"Bulk created {len(created)} normalized items")
        return created

    async def get_by_raw_item_id(self, raw_item_id: int) -> NormalizedItemDTO | None:
        """Get normalized item by raw item ID."""
        result = await self._session.execute(
            select(NormalizedItem).where(NormalizedItem.raw_item_id == raw_item_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return None
        return _to_dto(item)

    async def list_recent(self, *, limit: int = 100) -> list[NormalizedItemDTO]:
        """List recent normalized items."""
        result = await self._session.execute(
            select(NormalizedItem)
            .order_by(NormalizedItem.created_at.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        return [_to_dto(i) for i in items]

    async def search_candidates(
        self, *, board_type: str | None = None, limit: int = 100
    ) -> list[NormalizedItemDTO]:
        """Search candidate items for topic clustering."""
        stmt = select(NormalizedItem).order_by(NormalizedItem.published_at.desc())
        if board_type:
            stmt = stmt.where(NormalizedItem.board_type_candidate == board_type)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        items = result.scalars().all()
        return [_to_dto(i) for i in items]
