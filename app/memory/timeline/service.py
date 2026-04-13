"""Timeline Service for managing topic timelines."""

from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TimelinePointDTO
from app.memory.timeline.builder import TimelineBuilder
from app.memory.timeline.extractors import TimelineExtractor

if TYPE_CHECKING:
    from app.contracts.dto.normalized_item import NormalizedItemDTO
    from app.contracts.dto.topic import TopicReadDTO
    from app.memory.repositories.timeline_repository import TimelineRepository
    from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
    from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class TimelineService:
    """Service for building and managing topic timelines."""

    def __init__(
        self,
        timeline_repo: "TimelineRepository",
        topic_repo: "TopicRepository",
        item_repo: "NormalizedItemRepository",
        *,
        builder: TimelineBuilder | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            timeline_repo: Timeline repository.
            topic_repo: Topic repository.
            item_repo: Normalized item repository.
            builder: Optional timeline builder.
        """
        self._timeline_repo = timeline_repo
        self._topic_repo = topic_repo
        self._item_repo = item_repo
        self._builder = builder or TimelineBuilder()

    async def build_topic_timeline(
        self,
        topic_id: int,
        *,
        max_items: int = 100,
    ) -> list[TimelinePointDTO]:
        """Build timeline for a topic.

        Args:
            topic_id: The topic ID.
            max_items: Maximum items to process.

        Returns:
            List of TimelinePointDTO.
        """
        # Get topic
        topic = await self._topic_repo.get_by_id(topic_id)
        if topic is None:
            logger.warning(f"Topic {topic_id} not found")
            return []

        # Get topic items
        item_ids = await self._topic_repo.get_topic_items(topic_id, limit=max_items)
        items: list["NormalizedItemDTO"] = []
        for item_id in item_ids:
            item = await self._item_repo.get_by_id(item_id)
            if item:
                items.append(item)

        # Build timeline
        timeline = self._builder.build_from_items(items, topic)

        logger.info(f"Built timeline with {len(timeline)} events for topic {topic_id}")
        return timeline

    async def refresh_topic_timeline(
        self,
        topic_id: int,
        *,
        max_items: int = 100,
    ) -> list[TimelinePointDTO]:
        """Refresh and persist timeline for a topic.

        Deletes existing timeline events and creates new ones.

        Args:
            topic_id: The topic ID.
            max_items: Maximum items to process.

        Returns:
            List of persisted TimelinePointDTO.
        """
        # Build new timeline
        timeline = await self.build_topic_timeline(topic_id, max_items=max_items)

        if not timeline:
            return []

        # Delete existing events
        await self._timeline_repo.delete_by_topic(topic_id)

        # Persist new events
        events = await self._timeline_repo.bulk_create_events(timeline, topic_id)

        logger.info(f"Refreshed timeline with {len(events)} events for topic {topic_id}")
        return [
            TimelinePointDTO(
                event_time=e.event_time,
                event_type=e.event_type,
                title=e.title,
                description=e.description,
                source_item_id=e.source_item_id,
                source_type=e.source_type,
                importance_score=e.importance_score,
                metadata=e.metadata,
            )
            for e in events
        ]

    async def get_topic_timeline(
        self,
        topic_id: int,
        *,
        limit: int = 50,
    ) -> list[TimelinePointDTO]:
        """Get persisted timeline for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum events to return.

        Returns:
            List of TimelinePointDTO.
        """
        events = await self._timeline_repo.list_by_topic(topic_id, limit=limit)
        return [
            TimelinePointDTO(
                event_time=e.event_time,
                event_type=e.event_type,
                title=e.title,
                description=e.description,
                source_item_id=e.source_item_id,
                source_type=e.source_type,
                importance_score=e.importance_score,
                metadata=e.metadata,
            )
            for e in events
        ]

    async def get_topic_milestones(
        self,
        topic_id: int,
        *,
        limit: int = 20,
    ) -> list[TimelinePointDTO]:
        """Get milestone events for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum milestones to return.

        Returns:
            List of milestone TimelinePointDTO.
        """
        events = await self._timeline_repo.list_milestones(topic_id, limit=limit)
        return [
            TimelinePointDTO(
                event_time=e.event_time,
                event_type=e.event_type,
                title=e.title,
                description=e.description,
                source_item_id=e.source_item_id,
                source_type=e.source_type,
                importance_score=e.importance_score,
                metadata=e.metadata,
            )
            for e in events
        ]

    async def add_custom_event(
        self,
        topic_id: int,
        event: TimelinePointDTO,
    ) -> TimelinePointDTO | None:
        """Add a custom event to a topic's timeline.

        Args:
            topic_id: The topic ID.
            event: The event to add.

        Returns:
            Created TimelinePointDTO.
        """
        result = await self._timeline_repo.create_event(event, topic_id)
        return TimelinePointDTO(
            event_time=result.event_time,
            event_type=result.event_type,
            title=result.title,
            description=result.description,
            source_item_id=result.source_item_id,
            source_type=result.source_type,
            importance_score=result.importance_score,
            metadata=result.metadata,
        )
