"""Tag repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.tag import (
    TagCreateDTO,
    TagReadDTO,
    TagSummaryDTO,
    TagType,
    ItemTagDTO,
    TopicTagDTO,
)
from app.storage.db.models.tag import Tag
from app.storage.db.models.item_tag import ItemTag
from app.storage.db.models.topic_tag import TopicTag

logger = get_logger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize tag name for matching."""
    return name.lower().strip().replace(" ", "_").replace("-", "_")


def _to_read_dto(tag: Tag) -> TagReadDTO:
    """Convert ORM model to TagReadDTO."""
    return TagReadDTO(
        id=tag.id,
        name=tag.name,
        normalized_name=tag.normalized_name,
        tag_type=TagType(tag.tag_type),
        aliases=tag.aliases or [],
        description=tag.description,
        parent_tag_id=tag.parent_tag_id,
        created_at=tag.created_at,
    )


def _to_summary_dto(tag: Tag) -> TagSummaryDTO:
    """Convert ORM model to TagSummaryDTO."""
    return TagSummaryDTO(
        id=tag.id,
        name=tag.name,
        tag_type=TagType(tag.tag_type),
    )


class TagRepository:
    """Repository for tag operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: TagCreateDTO) -> TagReadDTO:
        """Create a new tag."""
        now = datetime.now(timezone.utc)
        normalized = _normalize_name(data.name)

        tag = Tag(
            name=data.name,
            normalized_name=normalized,
            tag_type=data.tag_type.value,
            aliases=data.aliases,
            description=data.description,
            parent_tag_id=data.parent_tag_id,
            created_at=now,
        )
        self._session.add(tag)
        await self._session.flush()
        logger.info(f"Created tag: {tag.name} (id={tag.id}, type={tag.tag_type})")
        return _to_read_dto(tag)

    async def get_by_id(self, tag_id: int) -> TagReadDTO | None:
        """Get tag by ID."""
        result = await self._session.execute(
            select(Tag).where(Tag.id == tag_id)
        )
        tag = result.scalar_one_or_none()
        if tag is None:
            return None
        return _to_read_dto(tag)

    async def get_by_name(self, name: str, tag_type: TagType) -> TagReadDTO | None:
        """Get tag by name and type."""
        normalized = _normalize_name(name)
        result = await self._session.execute(
            select(Tag)
            .where(Tag.normalized_name == normalized)
            .where(Tag.tag_type == tag_type.value)
        )
        tag = result.scalar_one_or_none()
        if tag is None:
            return None
        return _to_read_dto(tag)

    async def get_or_create(self, name: str, tag_type: TagType) -> TagReadDTO:
        """Get existing tag or create new one."""
        existing = await self.get_by_name(name, tag_type)
        if existing:
            return existing

        data = TagCreateDTO(name=name, tag_type=tag_type)
        return await self.create(data)

    async def list_by_type(self, tag_type: TagType, *, limit: int = 100) -> list[TagReadDTO]:
        """List tags by type."""
        result = await self._session.execute(
            select(Tag)
            .where(Tag.tag_type == tag_type.value)
            .order_by(Tag.name)
            .limit(limit)
        )
        tags = result.scalars().all()
        return [_to_read_dto(t) for t in tags]

    async def list_all(self, *, limit: int = 500) -> list[TagSummaryDTO]:
        """List all tags (summary view)."""
        result = await self._session.execute(
            select(Tag).order_by(Tag.tag_type, Tag.name).limit(limit)
        )
        tags = result.scalars().all()
        return [_to_summary_dto(t) for t in tags]

    async def search(self, query: str, *, limit: int = 20) -> list[TagSummaryDTO]:
        """Search tags by name."""
        normalized = _normalize_name(query)
        result = await self._session.execute(
            select(Tag)
            .where(Tag.normalized_name.ilike(f"%{normalized}%"))
            .order_by(Tag.name)
            .limit(limit)
        )
        tags = result.scalars().all()
        return [_to_summary_dto(t) for t in tags]

    # Item-Tag operations

    async def add_item_tag(
        self,
        item_id: int,
        tag_id: int,
        *,
        confidence: float = 1.0,
        source: str = "rule",
    ) -> bool:
        """Add a tag to an item."""
        link = ItemTag(
            item_id=item_id,
            tag_id=tag_id,
            confidence=confidence,
            source=source,
        )
        self._session.add(link)
        await self._session.flush()
        return True

    async def add_item_tags(
        self,
        item_id: int,
        tags: list[ItemTagDTO],
    ) -> int:
        """Add multiple tags to an item."""
        count = 0
        for tag_dto in tags:
            # Get or create the tag
            tag = await self.get_or_create(tag_dto.tag_name, tag_dto.tag_type)

            link = ItemTag(
                item_id=item_id,
                tag_id=tag.id,
                confidence=tag_dto.confidence,
                source=tag_dto.source,
            )
            self._session.add(link)
            count += 1

        await self._session.flush()
        logger.debug(f"Added {count} tags to item {item_id}")
        return count

    async def get_item_tags(self, item_id: int) -> list[ItemTagDTO]:
        """Get all tags for an item."""
        result = await self._session.execute(
            select(ItemTag, Tag)
            .join(Tag, ItemTag.tag_id == Tag.id)
            .where(ItemTag.item_id == item_id)
        )
        rows = result.all()

        return [
            ItemTagDTO(
                item_id=item_tag.item_id,
                tag_id=item_tag.tag_id,
                tag_name=tag.name,
                tag_type=TagType(tag.tag_type),
                confidence=float(item_tag.confidence),
                source=item_tag.source,
            )
            for item_tag, tag in rows
        ]

    async def remove_item_tags(self, item_id: int) -> int:
        """Remove all tags from an item."""
        result = await self._session.execute(
            delete(ItemTag).where(ItemTag.item_id == item_id)
        )
        await self._session.flush()
        return result.rowcount

    # Topic-Tag operations

    async def add_topic_tag(
        self,
        topic_id: int,
        tag_id: int,
        *,
        confidence: float = 1.0,
        item_count: int = 1,
        source: str = "aggregated",
    ) -> bool:
        """Add a tag to a topic."""
        link = TopicTag(
            topic_id=topic_id,
            tag_id=tag_id,
            confidence=confidence,
            item_count=item_count,
            source=source,
        )
        self._session.add(link)
        await self._session.flush()
        return True

    async def add_topic_tags(
        self,
        topic_id: int,
        tags: list[TopicTagDTO],
    ) -> int:
        """Add multiple tags to a topic."""
        count = 0
        for tag_dto in tags:
            # Get or create the tag
            tag = await self.get_or_create(tag_dto.tag_name, tag_dto.tag_type)

            link = TopicTag(
                topic_id=topic_id,
                tag_id=tag.id,
                confidence=tag_dto.confidence,
                item_count=tag_dto.item_count,
                source=tag_dto.source,
            )
            self._session.add(link)
            count += 1

        await self._session.flush()
        logger.debug(f"Added {count} tags to topic {topic_id}")
        return count

    async def get_topic_tags(self, topic_id: int) -> list[TopicTagDTO]:
        """Get all tags for a topic."""
        result = await self._session.execute(
            select(TopicTag, Tag)
            .join(Tag, TopicTag.tag_id == Tag.id)
            .where(TopicTag.topic_id == topic_id)
            .order_by(TopicTag.item_count.desc())
        )
        rows = result.all()

        return [
            TopicTagDTO(
                topic_id=topic_tag.topic_id,
                tag_id=topic_tag.tag_id,
                tag_name=tag.name,
                tag_type=TagType(tag.tag_type),
                confidence=float(topic_tag.confidence),
                item_count=topic_tag.item_count,
                source=topic_tag.source,
            )
            for topic_tag, tag in rows
        ]

    async def remove_topic_tags(self, topic_id: int) -> int:
        """Remove all tags from a topic."""
        result = await self._session.execute(
            delete(TopicTag).where(TopicTag.topic_id == topic_id)
        )
        await self._session.flush()
        return result.rowcount

    async def replace_topic_tags(
        self,
        topic_id: int,
        tags: list[TopicTagDTO],
    ) -> int:
        """Replace all tags for a topic."""
        await self.remove_topic_tags(topic_id)
        return await self.add_topic_tags(topic_id, tags)

    # Statistics

    async def count_by_type(self) -> dict[str, int]:
        """Count tags by type."""
        result = await self._session.execute(
            select(Tag.tag_type, func.count(Tag.id))
            .group_by(Tag.tag_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_popular_tags(
        self,
        tag_type: TagType | None = None,
        *,
        limit: int = 20,
    ) -> list[tuple[TagSummaryDTO, int]]:
        """Get most popular tags by item count."""
        query = (
            select(Tag, func.count(ItemTag.item_id).label("count"))
            .join(ItemTag, Tag.id == ItemTag.tag_id)
            .group_by(Tag.id)
            .order_by(func.count(ItemTag.item_id).desc())
            .limit(limit)
        )

        if tag_type:
            query = query.where(Tag.tag_type == tag_type.value)

        result = await self._session.execute(query)
        rows = result.all()

        return [(_to_summary_dto(tag), count) for tag, count in rows]
