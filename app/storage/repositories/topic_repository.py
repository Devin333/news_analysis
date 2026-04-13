"""Topic repository implementation."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType
from app.contracts.dto.topic import TopicCreateDTO, TopicReadDTO, TopicSummaryDTO
from app.storage.db.models.topic import Topic
from app.storage.db.models.topic_item import TopicItem

logger = get_logger(__name__)


def _to_read_dto(topic: Topic) -> TopicReadDTO:
    """Convert ORM model to TopicReadDTO."""
    return TopicReadDTO(
        id=topic.id,
        board_type=BoardType(topic.board_type),
        topic_type=topic.topic_type,
        title=topic.title,
        summary=topic.summary,
        representative_item_id=topic.representative_item_id,
        first_seen_at=topic.first_seen_at,
        last_seen_at=topic.last_seen_at,
        item_count=topic.item_count,
        source_count=topic.source_count,
        heat_score=float(topic.heat_score),
        trend_score=float(topic.trend_score),
        status=topic.status,
        metadata_json=topic.metadata_json,
    )


def _to_summary_dto(topic: Topic) -> TopicSummaryDTO:
    """Convert ORM model to TopicSummaryDTO."""
    return TopicSummaryDTO(
        id=topic.id,
        title=topic.title,
        board_type=BoardType(topic.board_type),
        item_count=topic.item_count,
        source_count=topic.source_count,
        heat_score=float(topic.heat_score),
        last_seen_at=topic.last_seen_at,
    )


class TopicRepository:
    """Topic repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: TopicCreateDTO) -> TopicReadDTO:
        """Create a new topic."""
        now = datetime.now(timezone.utc)
        topic = Topic(
            board_type=data.board_type.value,
            topic_type=data.topic_type,
            title=data.title,
            summary=data.summary,
            representative_item_id=data.representative_item_id,
            first_seen_at=now,
            last_seen_at=now,
            item_count=0,
            source_count=0,
            heat_score=0.0,
            trend_score=0.0,
            status="active",
            metadata_json=data.metadata_json,
        )
        self._session.add(topic)
        await self._session.flush()
        logger.info(f"Created topic: {topic.title} (id={topic.id})")
        return _to_read_dto(topic)

    async def get_by_id(self, topic_id: int) -> TopicReadDTO | None:
        """Get topic by ID."""
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            return None
        return _to_read_dto(topic)

    async def list_recent(self, *, limit: int = 100) -> list[TopicReadDTO]:
        """List recent topics."""
        result = await self._session.execute(
            select(Topic)
            .where(Topic.status == "active")
            .order_by(Topic.last_seen_at.desc())
            .limit(limit)
        )
        topics = result.scalars().all()
        return [_to_read_dto(t) for t in topics]

    async def list_recent_summaries(self, *, limit: int = 100) -> list[TopicSummaryDTO]:
        """List recent topic summaries (lightweight)."""
        result = await self._session.execute(
            select(Topic)
            .where(Topic.status == "active")
            .order_by(Topic.last_seen_at.desc())
            .limit(limit)
        )
        topics = result.scalars().all()
        return [_to_summary_dto(t) for t in topics]

    async def list_by_board(
        self, board_type: BoardType, *, limit: int = 100
    ) -> list[TopicReadDTO]:
        """List topics by board type."""
        result = await self._session.execute(
            select(Topic)
            .where(Topic.board_type == board_type.value)
            .where(Topic.status == "active")
            .order_by(Topic.last_seen_at.desc())
            .limit(limit)
        )
        topics = result.scalars().all()
        return [_to_read_dto(t) for t in topics]

    async def find_candidates(
        self,
        *,
        board_type: BoardType | None = None,
        days: int = 7,
        limit: int = 50,
    ) -> list[TopicReadDTO]:
        """Find candidate topics for merge evaluation.

        Args:
            board_type: Filter by board type.
            days: Look back period in days.
            limit: Maximum candidates to return.

        Returns:
            List of candidate topics.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = (
            select(Topic)
            .where(Topic.status == "active")
            .where(Topic.last_seen_at >= cutoff)
        )

        if board_type:
            query = query.where(Topic.board_type == board_type.value)

        query = query.order_by(Topic.last_seen_at.desc()).limit(limit)

        result = await self._session.execute(query)
        topics = result.scalars().all()
        return [_to_read_dto(t) for t in topics]

    async def add_item(
        self, topic_id: int, item_id: int, *, link_reason: str | None = None
    ) -> bool:
        """Add an item to a topic."""
        link = TopicItem(topic_id=topic_id, item_id=item_id, link_reason=link_reason)
        self._session.add(link)
        await self._session.flush()
        logger.info(f"Added item {item_id} to topic {topic_id}")
        return True

    async def get_topic_items(self, topic_id: int, *, limit: int = 100) -> list[int]:
        """Get item IDs for a topic."""
        result = await self._session.execute(
            select(TopicItem.item_id)
            .where(TopicItem.topic_id == topic_id)
            .order_by(TopicItem.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_metrics(
        self,
        topic_id: int,
        *,
        item_count: int | None = None,
        source_count: int | None = None,
        heat_score: float | None = None,
        trend_score: float | None = None,
        last_seen_at: datetime | None = None,
    ) -> bool:
        """Update topic metrics."""
        values: dict[str, Any] = {}
        if item_count is not None:
            values["item_count"] = item_count
        if source_count is not None:
            values["source_count"] = source_count
        if heat_score is not None:
            values["heat_score"] = heat_score
        if trend_score is not None:
            values["trend_score"] = trend_score
        if last_seen_at is not None:
            values["last_seen_at"] = last_seen_at

        if not values:
            return False

        result = await self._session.execute(
            update(Topic).where(Topic.id == topic_id).values(**values)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def update_summary(
        self, topic_id: int, summary: str | None = None, representative_item_id: int | None = None
    ) -> bool:
        """Update topic summary and/or representative item."""
        values: dict[str, Any] = {}
        if summary is not None:
            values["summary"] = summary
        if representative_item_id is not None:
            values["representative_item_id"] = representative_item_id

        if not values:
            return False

        result = await self._session.execute(
            update(Topic).where(Topic.id == topic_id).values(**values)
        )
        await self._session.flush()
        return result.rowcount > 0

    async def count_items(self, topic_id: int) -> int:
        """Count items in a topic."""
        result = await self._session.execute(
            select(func.count()).select_from(TopicItem).where(TopicItem.topic_id == topic_id)
        )
        return result.scalar_one()
