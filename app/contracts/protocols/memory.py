"""Memory layer protocols for complex memory system.

This module defines the unified protocols for memory repositories and services.
All memory access should go through these protocols.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from app.contracts.dto.memory import (
    EntityMemoryCreateDTO,
    EntityMemoryDTO,
    JudgementCreateDTO,
    JudgementMemoryDTO,
    MemoryRetrievalResultDTO,
    TimelineEventDTO,
    TimelinePointDTO,
    TopicHistoryContextDTO,
    TopicMemoryCreateDTO,
    TopicMemoryDTO,
    TopicSnapshotCreateDTO,
    TopicSnapshotDTO,
)


# ============ Topic Memory Repository Protocol ============


@runtime_checkable
class TopicMemoryRepositoryProtocol(Protocol):
    """Protocol for topic memory repository."""

    @abstractmethod
    async def get_by_topic_id(self, topic_id: int) -> TopicMemoryDTO | None:
        """Get topic memory by topic ID.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicMemoryDTO if found, None otherwise.
        """
        ...

    @abstractmethod
    async def create(self, data: TopicMemoryCreateDTO) -> TopicMemoryDTO:
        """Create a new topic memory.

        Args:
            data: Topic memory creation data.

        Returns:
            Created TopicMemoryDTO.
        """
        ...

    @abstractmethod
    async def update(
        self,
        topic_id: int,
        data: dict,
    ) -> TopicMemoryDTO | None:
        """Update topic memory.

        Args:
            topic_id: The topic ID.
            data: Fields to update.

        Returns:
            Updated TopicMemoryDTO if found, None otherwise.
        """
        ...

    @abstractmethod
    async def create_snapshot(
        self,
        data: TopicSnapshotCreateDTO,
    ) -> TopicSnapshotDTO:
        """Create a topic snapshot.

        Args:
            data: Snapshot creation data.

        Returns:
            Created TopicSnapshotDTO.
        """
        ...

    @abstractmethod
    async def list_snapshots(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[TopicSnapshotDTO]:
        """List snapshots for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of snapshots to return.

        Returns:
            List of TopicSnapshotDTO.
        """
        ...

    @abstractmethod
    async def get_latest_snapshot(
        self,
        topic_id: int,
    ) -> TopicSnapshotDTO | None:
        """Get the latest snapshot for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            Latest TopicSnapshotDTO if exists, None otherwise.
        """
        ...


# ============ Entity Memory Repository Protocol ============


@runtime_checkable
class EntityMemoryRepositoryProtocol(Protocol):
    """Protocol for entity memory repository."""

    @abstractmethod
    async def get_by_entity_id(self, entity_id: int) -> EntityMemoryDTO | None:
        """Get entity memory by entity ID.

        Args:
            entity_id: The entity ID.

        Returns:
            EntityMemoryDTO if found, None otherwise.
        """
        ...

    @abstractmethod
    async def create_or_update(
        self,
        data: EntityMemoryCreateDTO,
    ) -> EntityMemoryDTO:
        """Create or update entity memory.

        Args:
            data: Entity memory data.

        Returns:
            Created or updated EntityMemoryDTO.
        """
        ...

    @abstractmethod
    async def list_related_topics(
        self,
        entity_id: int,
        limit: int = 20,
    ) -> list[int]:
        """List topic IDs related to an entity.

        Args:
            entity_id: The entity ID.
            limit: Maximum number of topics to return.

        Returns:
            List of topic IDs.
        """
        ...

    @abstractmethod
    async def attach_topic_entity(
        self,
        topic_id: int,
        entity_id: int,
        relevance_score: float = 1.0,
    ) -> None:
        """Attach an entity to a topic.

        Args:
            topic_id: The topic ID.
            entity_id: The entity ID.
            relevance_score: Relevance score of the relationship.
        """
        ...


# ============ Judgement Memory Repository Protocol ============


@runtime_checkable
class JudgementMemoryRepositoryProtocol(Protocol):
    """Protocol for judgement memory repository."""

    @abstractmethod
    async def create_log(self, data: JudgementCreateDTO) -> JudgementMemoryDTO:
        """Create a judgement log.

        Args:
            data: Judgement creation data.

        Returns:
            Created JudgementMemoryDTO.
        """
        ...

    @abstractmethod
    async def list_by_target(
        self,
        target_type: str,
        target_id: int,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """List judgements for a target.

        Args:
            target_type: Type of target (topic, entity, item).
            target_id: ID of the target.
            limit: Maximum number of judgements to return.

        Returns:
            List of JudgementMemoryDTO.
        """
        ...

    @abstractmethod
    async def list_recent_by_type(
        self,
        judgement_type: str,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """List recent judgements by type.

        Args:
            judgement_type: Type of judgement.
            limit: Maximum number of judgements to return.

        Returns:
            List of JudgementMemoryDTO.
        """
        ...

    @abstractmethod
    async def find_similar_judgements(
        self,
        judgement: str,
        limit: int = 10,
    ) -> list[JudgementMemoryDTO]:
        """Find similar judgements (stub for future implementation).

        Args:
            judgement: Judgement text to find similar ones.
            limit: Maximum number of judgements to return.

        Returns:
            List of similar JudgementMemoryDTO.
        """
        ...


# ============ Timeline Repository Protocol ============


@runtime_checkable
class TimelineRepositoryProtocol(Protocol):
    """Protocol for timeline repository."""

    @abstractmethod
    async def create_event(self, data: TimelinePointDTO, topic_id: int) -> TimelineEventDTO:
        """Create a timeline event.

        Args:
            data: Timeline point data.
            topic_id: The topic ID.

        Returns:
            Created TimelineEventDTO.
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def list_by_time_range(
        self,
        topic_id: int,
        start_time: str,
        end_time: str,
    ) -> list[TimelineEventDTO]:
        """List timeline events within a time range.

        Args:
            topic_id: The topic ID.
            start_time: Start time (ISO format).
            end_time: End time (ISO format).

        Returns:
            List of TimelineEventDTO within the range.
        """
        ...


# ============ Memory Retrieval Protocol ============


@runtime_checkable
class MemoryRetrievalProtocol(Protocol):
    """Protocol for unified memory retrieval."""

    @abstractmethod
    async def retrieve_topic_history(
        self,
        topic_id: int,
    ) -> TopicHistoryContextDTO:
        """Retrieve complete historical context for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicHistoryContextDTO with all historical context.
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def retrieve_related_topics(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[int]:
        """Retrieve related topic IDs.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of related topics.

        Returns:
            List of related topic IDs.
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def retrieve_full_context(
        self,
        topic_id: int,
    ) -> MemoryRetrievalResultDTO:
        """Retrieve full memory context for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            MemoryRetrievalResultDTO with all available context.
        """
        ...
