"""Topic repository implementation."""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.topic import Topic
from app.storage.db.models.topic_item import TopicItem

logger = get_logger(__name__)


class TopicDTO:
    """Topic data transfer object."""

    def __init__(
        self,
        *,
        id: int | None = None,
        board_type: str = "general",
        topic_type: str = "auto",
        title: str,
        summary: str | None = None,
        representative_item_id: int | None = None,
        first_seen_at: datetime | None = None,
        last_seen_at: datetime | None = None,
        item_count: int = 0,
        source_count: int = 0,
        heat_score: float = 0.0,
        trend_score: float = 0.0,
        status: str = "active",
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.board_type = board_type
        self.topic_type = topic_type
        self.title = title
        self.summary = summary
        self.representative_item_id = representative_item_id
        self.first_seen_at = first_seen_at
        self.last_seen_at = last_seen_at
        self.item_count = item_count
        self.source_count = source_count
        self.heat_score = heat_score
        self.trend_score = trend_score
        self.status = status
        self.metadata_json = metadata_json or {}


def _to_dto(topic: Topic) -> TopicDTO:
    """Convert ORM model to TopicDTO."""
    return TopicDTO(
        id=topic.id,
        board_type=topic.board_type,
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


class TopicRepository:
    """Topic repository for CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_topic(self, data: TopicDTO) -> TopicDTO:
        """Create a new topic."""
        topic = Topic(
            board_type=data.board_type,
            topic_type=data.topic_type,
            title=data.title,
            summary=data.summary,
            representative_item_id=data.representative_item_id,
            item_count=data.item_count,
            source_count=data.source_count,
            heat_score=data.heat_score,
            trend_score=data.trend_score,
            status=data.status,
            metadata_json=data.metadata_json,
        )
        self._session.add(topic)
        await self._session.flush()
        logger.info(f"Created topic: {topic.title} (id={topic.id})")
        return _to_dto(topic)

    async def get_by_id(self, topic_id: int) -> TopicDTO | None:
        """Get topic by ID."""
        result = await self._session.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        if topic is None:
            return None
        return _to_dto(topic)

    async def list_recent(self, *, limit: int = 100) -> list[TopicDTO]:
        """List recent topics."""
        result = await self._session.execute(
            select(Topic)
            .where(Topic.status == "active")
            .order_by(Topic.last_seen_at.desc())
            .limit(limit)
        )
        topics = result.scalars().all()
        return [_to_dto(t) for t in topics]

    async def add_item_to_topic(
        self, topic_id: int, item_id: int, *, link_reason: str | None = None
    ) -> bool:
        """Add an item to a topic."""
        link = TopicItem(topic_id=topic_id, item_id=item_id, link_reason=link_reason)
        self._session.add(link)
        await self._session.flush()
        logger.info(f"Added item {item_id} to topic {topic_id}")
        return True

    async def update_metrics(
        self,
        topic_id: int,
        *,
        item_count: int | None = None,
        source_count: int | None = None,
        heat_score: float | None = None,
        trend_score: float | None = None,
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

        if not values:
            return False

        result = await self._session.execute(
            update(Topic).where(Topic.id == topic_id).values(**values)
        )
        await self._session.flush()
        return result.rowcount > 0
