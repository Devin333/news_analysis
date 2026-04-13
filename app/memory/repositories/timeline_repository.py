"""Timeline Repository implementation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TimelineEventDTO, TimelinePointDTO
from app.storage.db.models.topic_timeline_event import TopicTimelineEvent

logger = get_logger(__name__)


class TimelineRepository:
    """Repository for timeline event operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create_event(
        self,
        data: TimelinePointDTO,
        topic_id: int,
    ) -> TimelineEventDTO:
        """Create a timeline event.

        Args:
            data: Timeline point data.
            topic_id: The topic ID.

        Returns:
            Created TimelineEventDTO.
        """
        model = TopicTimelineEvent(
            topic_id=topic_id,
            event_time=data.event_time,
            event_type=data.event_type,
            title=data.title,
            description=data.description,
            source_item_id=data.source_item_id,
            source_type=data.source_type,
            importance_score=data.importance_score,
            is_milestone=data.importance_score >= 0.8,
            metadata_json=data.metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created timeline event '{data.title}' for topic {topic_id}")
        return self._to_dto(model)

    async def bulk_create_events(
        self,
        events: list[TimelinePointDTO],
        topic_id: int,
    ) -> list[TimelineEventDTO]:
        """Bulk create timeline events.

        Args:
            events: List of timeline points.
            topic_id: The topic ID.

        Returns:
            List of created TimelineEventDTO.
        """
        if not events:
            return []

        models = [
            TopicTimelineEvent(
                topic_id=topic_id,
                event_time=e.event_time,
                event_type=e.event_type,
                title=e.title,
                description=e.description,
                source_item_id=e.source_item_id,
                source_type=e.source_type,
                importance_score=e.importance_score,
                is_milestone=e.importance_score >= 0.8,
                metadata_json=e.metadata,
            )
            for e in events
        ]

        self._session.add_all(models)
        await self._session.flush()

        # Refresh all models
        for model in models:
            await self._session.refresh(model)

        logger.info(f"Created {len(models)} timeline events for topic {topic_id}")
        return [self._to_dto(m) for m in models]

    async def list_by_topic(
        self,
        topic_id: int,
        limit: int = 50,
    ) -> list[TimelineEventDTO]:
        """List timeline events for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of events to return.

        Returns:
            List of TimelineEventDTO ordered by event_time.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(TopicTimelineEvent.topic_id == topic_id)
            .order_by(TopicTimelineEvent.event_time.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def list_by_time_range(
        self,
        topic_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> list[TimelineEventDTO]:
        """List timeline events within a time range.

        Args:
            topic_id: The topic ID.
            start_time: Start time.
            end_time: End time.

        Returns:
            List of TimelineEventDTO within the range.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(
                TopicTimelineEvent.topic_id == topic_id,
                TopicTimelineEvent.event_time >= start_time,
                TopicTimelineEvent.event_time <= end_time,
            )
            .order_by(TopicTimelineEvent.event_time.asc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def list_milestones(
        self,
        topic_id: int,
        limit: int = 20,
    ) -> list[TimelineEventDTO]:
        """List milestone events for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of events.

        Returns:
            List of milestone TimelineEventDTO.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(
                TopicTimelineEvent.topic_id == topic_id,
                TopicTimelineEvent.is_milestone == True,  # noqa: E712
            )
            .order_by(TopicTimelineEvent.event_time.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def list_by_event_type(
        self,
        topic_id: int,
        event_type: str,
        limit: int = 50,
    ) -> list[TimelineEventDTO]:
        """List events by type for a topic.

        Args:
            topic_id: The topic ID.
            event_type: Type of event.
            limit: Maximum number of events.

        Returns:
            List of TimelineEventDTO.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(
                TopicTimelineEvent.topic_id == topic_id,
                TopicTimelineEvent.event_type == event_type,
            )
            .order_by(TopicTimelineEvent.event_time.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._to_dto(row) for row in rows]

    async def delete_by_topic(self, topic_id: int) -> int:
        """Delete all timeline events for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            Number of deleted events.
        """
        from sqlalchemy import delete

        stmt = delete(TopicTimelineEvent).where(
            TopicTimelineEvent.topic_id == topic_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()

        count = result.rowcount
        logger.info(f"Deleted {count} timeline events for topic {topic_id}")
        return count

    async def get_latest_event(
        self,
        topic_id: int,
    ) -> TimelineEventDTO | None:
        """Get the latest timeline event for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            Latest TimelineEventDTO if exists.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(TopicTimelineEvent.topic_id == topic_id)
            .order_by(TopicTimelineEvent.event_time.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._to_dto(row)

    async def get_first_event(
        self,
        topic_id: int,
    ) -> TimelineEventDTO | None:
        """Get the first timeline event for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            First TimelineEventDTO if exists.
        """
        stmt = (
            select(TopicTimelineEvent)
            .where(TopicTimelineEvent.topic_id == topic_id)
            .order_by(TopicTimelineEvent.event_time.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._to_dto(row)

    def _to_dto(self, model: TopicTimelineEvent) -> TimelineEventDTO:
        """Convert ORM model to DTO."""
        return TimelineEventDTO(
            id=model.id,
            topic_id=model.topic_id,
            event_time=model.event_time,
            event_type=model.event_type,
            title=model.title,
            description=model.description,
            source_item_id=model.source_item_id,
            source_type=model.source_type,
            importance_score=model.importance_score,
            metadata=model.metadata_json or {},
            created_at=model.created_at,
        )
