"""Memory Retrieval Service for unified historical context retrieval.

Provides a single entry point for agents to retrieve all relevant
historical context for topics and entities.
"""

import time
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import (
    EntityMemoryDTO,
    JudgementMemoryDTO,
    MemoryRetrievalResultDTO,
    TimelinePointDTO,
    TopicHistoryContextDTO,
    TopicMemoryDTO,
    TopicSnapshotDTO,
)

if TYPE_CHECKING:
    from app.memory.repositories.entity_memory_repository import EntityMemoryRepository
    from app.memory.repositories.judgement_repository import JudgementRepository
    from app.memory.repositories.timeline_repository import TimelineRepository
    from app.memory.repositories.topic_memory_repository import TopicMemoryRepository
    from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class MemoryRetrievalService:
    """Unified memory retrieval service.

    Provides methods for retrieving historical context for topics
    and entities. This is the main interface for agents to access
    memory without directly querying repositories.
    """

    def __init__(
        self,
        topic_memory_repo: "TopicMemoryRepository",
        entity_memory_repo: "EntityMemoryRepository",
        judgement_repo: "JudgementRepository",
        timeline_repo: "TimelineRepository",
        topic_repo: "TopicRepository | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            topic_memory_repo: Topic memory repository.
            entity_memory_repo: Entity memory repository.
            judgement_repo: Judgement repository.
            timeline_repo: Timeline repository.
            topic_repo: Optional topic repository for related topics.
        """
        self._topic_memory_repo = topic_memory_repo
        self._entity_memory_repo = entity_memory_repo
        self._judgement_repo = judgement_repo
        self._timeline_repo = timeline_repo
        self._topic_repo = topic_repo

    async def retrieve_topic_history(
        self,
        topic_id: int,
    ) -> TopicHistoryContextDTO:
        """Retrieve complete historical context for a topic.

        This is the main method for Historian/Analyst agents to get
        all relevant historical context.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicHistoryContextDTO with all historical context.
        """
        # Get topic memory
        topic_memory = await self._topic_memory_repo.get_by_topic_id(topic_id)

        # Get latest snapshot
        latest_snapshot = await self._topic_memory_repo.get_latest_snapshot(topic_id)

        # Get timeline
        timeline_events = await self._timeline_repo.list_by_topic(topic_id, limit=50)
        timeline = [
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
            for e in timeline_events
        ]

        # Get related entity IDs (from topic-entity relationships)
        related_entity_ids: list[int] = []
        # TODO: Implement when topic-entity queries are available

        # Get recent judgements
        judgements = await self._judgement_repo.list_by_target("topic", topic_id, limit=10)

        # Get similar past topics (stub for now)
        similar_past_topics: list[int] = []

        return TopicHistoryContextDTO(
            topic_id=topic_id,
            topic_memory=topic_memory,
            latest_snapshot=latest_snapshot,
            timeline=timeline,
            related_entity_ids=related_entity_ids,
            recent_judgements=judgements,
            similar_past_topics=similar_past_topics,
        )

    async def retrieve_entity_history(
        self,
        entity_id: int,
    ) -> EntityMemoryDTO | None:
        """Retrieve entity memory.

        Args:
            entity_id: The entity ID.

        Returns:
            EntityMemoryDTO if found, None otherwise.
        """
        return await self._entity_memory_repo.get_by_entity_id(entity_id)

    async def retrieve_related_topics(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[int]:
        """Retrieve related topic IDs.

        Currently returns topics that share entities with the given topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of related topics.

        Returns:
            List of related topic IDs.
        """
        # TODO: Implement based on shared entities, tags, or embeddings
        return []

    async def retrieve_recent_topic_items(
        self,
        topic_id: int,
        limit: int = 20,
    ) -> list[int]:
        """Retrieve recent item IDs for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of items.

        Returns:
            List of item IDs.
        """
        if self._topic_repo is None:
            return []
        return await self._topic_repo.get_topic_items(topic_id, limit=limit)

    async def retrieve_topic_snapshots(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[TopicSnapshotDTO]:
        """Retrieve topic snapshots.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of snapshots.

        Returns:
            List of TopicSnapshotDTO.
        """
        return await self._topic_memory_repo.list_snapshots(topic_id, limit)

    async def retrieve_topic_timeline(
        self,
        topic_id: int,
        limit: int = 50,
    ) -> list[TimelinePointDTO]:
        """Retrieve topic timeline.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of timeline points.

        Returns:
            List of TimelinePointDTO.
        """
        events = await self._timeline_repo.list_by_topic(topic_id, limit)
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

    async def retrieve_full_context(
        self,
        topic_id: int,
    ) -> MemoryRetrievalResultDTO:
        """Retrieve full memory context for a topic.

        This is the most comprehensive retrieval method, returning
        all available memory data for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            MemoryRetrievalResultDTO with all available context.
        """
        start = time.time()

        # Get topic memory
        topic_memory = await self._topic_memory_repo.get_by_topic_id(topic_id)

        # Get snapshots
        snapshots = await self._topic_memory_repo.list_snapshots(topic_id, limit=10)

        # Get timeline
        timeline_events = await self._timeline_repo.list_by_topic(topic_id, limit=50)
        timeline = [
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
            for e in timeline_events
        ]

        # Get entity memories (stub - would need topic-entity relationships)
        entity_memories: list[EntityMemoryDTO] = []

        # Get related topics
        related_topics = await self.retrieve_related_topics(topic_id)

        # Get judgements
        judgements = await self._judgement_repo.list_by_target("topic", topic_id, limit=20)

        elapsed_ms = (time.time() - start) * 1000

        return MemoryRetrievalResultDTO(
            topic_memory=topic_memory,
            snapshots=snapshots,
            timeline=timeline,
            entity_memories=entity_memories,
            related_topics=related_topics,
            judgements=judgements,
            retrieval_time_ms=elapsed_ms,
        )

    async def retrieve_topic_judgements(
        self,
        topic_id: int,
        judgement_type: str | None = None,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Retrieve judgements for a topic.

        Args:
            topic_id: The topic ID.
            judgement_type: Optional filter by judgement type.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        judgements = await self._judgement_repo.list_by_target("topic", topic_id, limit)

        if judgement_type:
            judgements = [j for j in judgements if j.judgement_type == judgement_type]

        return judgements

    async def retrieve_entity_related_topics(
        self,
        entity_id: int,
        limit: int = 20,
    ) -> list[int]:
        """Retrieve topics related to an entity.

        Args:
            entity_id: The entity ID.
            limit: Maximum number of topics.

        Returns:
            List of topic IDs.
        """
        return await self._entity_memory_repo.list_related_topics(entity_id, limit)
