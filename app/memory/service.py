"""Memory Service for unified memory access.

This service provides the single entry point for all memory operations.
Agents should only access memory through this service, not directly
through repositories.
"""

from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import (
    EntityMemoryCreateDTO,
    EntityMemoryDTO,
    JudgementCreateDTO,
    JudgementMemoryDTO,
    MemoryRetrievalResultDTO,
    TimelinePointDTO,
    TopicHistoryContextDTO,
    TopicMemoryCreateDTO,
    TopicMemoryDTO,
    TopicSnapshotCreateDTO,
    TopicSnapshotDTO,
)

if TYPE_CHECKING:
    from app.contracts.protocols.memory import (
        EntityMemoryRepositoryProtocol,
        JudgementMemoryRepositoryProtocol,
        TimelineRepositoryProtocol,
        TopicMemoryRepositoryProtocol,
    )

logger = get_logger(__name__)


class MemoryService:
    """Unified memory service for all memory operations.

    This service aggregates all memory repositories and provides
    a clean interface for agents to access memory.
    """

    def __init__(
        self,
        topic_memory_repo: "TopicMemoryRepositoryProtocol | None" = None,
        entity_memory_repo: "EntityMemoryRepositoryProtocol | None" = None,
        judgement_repo: "JudgementMemoryRepositoryProtocol | None" = None,
        timeline_repo: "TimelineRepositoryProtocol | None" = None,
    ) -> None:
        """Initialize the memory service.

        Args:
            topic_memory_repo: Repository for topic memory.
            entity_memory_repo: Repository for entity memory.
            judgement_repo: Repository for judgement memory.
            timeline_repo: Repository for timeline events.
        """
        self._topic_memory_repo = topic_memory_repo
        self._entity_memory_repo = entity_memory_repo
        self._judgement_repo = judgement_repo
        self._timeline_repo = timeline_repo

    # ============ Topic Memory Methods ============

    async def get_topic_memory(self, topic_id: int) -> TopicMemoryDTO | None:
        """Get topic memory by topic ID.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicMemoryDTO if found, None otherwise.
        """
        if self._topic_memory_repo is None:
            logger.warning("Topic memory repository not configured")
            return None
        return await self._topic_memory_repo.get_by_topic_id(topic_id)

    async def create_or_update_topic_memory(
        self,
        topic_id: int,
        data: TopicMemoryCreateDTO | dict,
    ) -> TopicMemoryDTO | None:
        """Create or update topic memory.

        Args:
            topic_id: The topic ID.
            data: Topic memory data (DTO or dict for update).

        Returns:
            Created or updated TopicMemoryDTO.
        """
        if self._topic_memory_repo is None:
            logger.warning("Topic memory repository not configured")
            return None

        existing = await self._topic_memory_repo.get_by_topic_id(topic_id)
        if existing:
            update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
            return await self._topic_memory_repo.update(topic_id, update_data)
        else:
            if isinstance(data, dict):
                create_dto = TopicMemoryCreateDTO(topic_id=topic_id, **data)
            else:
                create_dto = data
            return await self._topic_memory_repo.create(create_dto)

    async def create_topic_snapshot(
        self,
        topic_id: int,
        snapshot: TopicSnapshotCreateDTO,
    ) -> TopicSnapshotDTO | None:
        """Create a topic snapshot.

        Args:
            topic_id: The topic ID.
            snapshot: Snapshot data.

        Returns:
            Created TopicSnapshotDTO.
        """
        if self._topic_memory_repo is None:
            logger.warning("Topic memory repository not configured")
            return None

        # Ensure topic_id is set
        if snapshot.topic_id != topic_id:
            snapshot = TopicSnapshotCreateDTO(
                topic_id=topic_id,
                **snapshot.model_dump(exclude={"topic_id"}),
            )
        return await self._topic_memory_repo.create_snapshot(snapshot)

    async def get_topic_snapshots(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[TopicSnapshotDTO]:
        """Get snapshots for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of snapshots.

        Returns:
            List of TopicSnapshotDTO.
        """
        if self._topic_memory_repo is None:
            return []
        return await self._topic_memory_repo.list_snapshots(topic_id, limit)

    async def get_latest_topic_snapshot(
        self,
        topic_id: int,
    ) -> TopicSnapshotDTO | None:
        """Get the latest snapshot for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            Latest TopicSnapshotDTO if exists.
        """
        if self._topic_memory_repo is None:
            return None
        return await self._topic_memory_repo.get_latest_snapshot(topic_id)

    # ============ Entity Memory Methods ============

    async def get_entity_memory(self, entity_id: int) -> EntityMemoryDTO | None:
        """Get entity memory by entity ID.

        Args:
            entity_id: The entity ID.

        Returns:
            EntityMemoryDTO if found, None otherwise.
        """
        if self._entity_memory_repo is None:
            logger.warning("Entity memory repository not configured")
            return None
        return await self._entity_memory_repo.get_by_entity_id(entity_id)

    async def refresh_entity_memory(
        self,
        entity_id: int,
        data: EntityMemoryCreateDTO,
    ) -> EntityMemoryDTO | None:
        """Refresh (create or update) entity memory.

        Args:
            entity_id: The entity ID.
            data: Entity memory data.

        Returns:
            Updated EntityMemoryDTO.
        """
        if self._entity_memory_repo is None:
            logger.warning("Entity memory repository not configured")
            return None

        # Ensure entity_id matches
        if data.entity_id != entity_id:
            data = EntityMemoryCreateDTO(
                entity_id=entity_id,
                **data.model_dump(exclude={"entity_id"}),
            )
        return await self._entity_memory_repo.create_or_update(data)

    async def get_entity_related_topics(
        self,
        entity_id: int,
        limit: int = 20,
    ) -> list[int]:
        """Get topic IDs related to an entity.

        Args:
            entity_id: The entity ID.
            limit: Maximum number of topics.

        Returns:
            List of topic IDs.
        """
        if self._entity_memory_repo is None:
            return []
        return await self._entity_memory_repo.list_related_topics(entity_id, limit)

    # ============ Judgement Memory Methods ============

    async def create_judgement_log(
        self,
        data: JudgementCreateDTO,
    ) -> JudgementMemoryDTO | None:
        """Create a judgement log.

        Args:
            data: Judgement data.

        Returns:
            Created JudgementMemoryDTO.
        """
        if self._judgement_repo is None:
            logger.warning("Judgement repository not configured")
            return None
        return await self._judgement_repo.create_log(data)

    async def get_judgements_for_target(
        self,
        target_type: str,
        target_id: int,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Get judgements for a target.

        Args:
            target_type: Type of target (topic, entity, item).
            target_id: ID of the target.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        if self._judgement_repo is None:
            return []
        return await self._judgement_repo.list_by_target(target_type, target_id, limit)

    async def get_recent_judgements_by_type(
        self,
        judgement_type: str,
        limit: int = 20,
    ) -> list[JudgementMemoryDTO]:
        """Get recent judgements by type.

        Args:
            judgement_type: Type of judgement.
            limit: Maximum number of judgements.

        Returns:
            List of JudgementMemoryDTO.
        """
        if self._judgement_repo is None:
            return []
        return await self._judgement_repo.list_recent_by_type(judgement_type, limit)

    # ============ Timeline Methods ============

    async def get_topic_timeline(
        self,
        topic_id: int,
        limit: int = 50,
    ) -> list[TimelinePointDTO]:
        """Get timeline for a topic.

        Args:
            topic_id: The topic ID.
            limit: Maximum number of events.

        Returns:
            List of TimelinePointDTO.
        """
        if self._timeline_repo is None:
            return []
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

    # ============ Retrieval Methods ============

    async def retrieve_topic_context(
        self,
        topic_id: int,
    ) -> TopicHistoryContextDTO:
        """Retrieve complete historical context for a topic.

        This is the main method for agents to get all relevant
        historical context for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicHistoryContextDTO with all available context.
        """
        topic_memory = await self.get_topic_memory(topic_id)
        latest_snapshot = await self.get_latest_topic_snapshot(topic_id)
        timeline = await self.get_topic_timeline(topic_id)
        judgements = await self.get_judgements_for_target("topic", topic_id)

        # Get related entities (stub - will be implemented with entity memory)
        related_entity_ids: list[int] = []

        # Get similar past topics (stub - will be implemented with retrieval)
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

    async def get_topic_historical_context(
        self,
        topic_id: int,
    ) -> MemoryRetrievalResultDTO:
        """Get full memory retrieval result for a topic.

        Args:
            topic_id: The topic ID.

        Returns:
            MemoryRetrievalResultDTO with all memory data.
        """
        import time

        start = time.time()

        topic_memory = await self.get_topic_memory(topic_id)
        snapshots = await self.get_topic_snapshots(topic_id)
        timeline = await self.get_topic_timeline(topic_id)
        judgements = await self.get_judgements_for_target("topic", topic_id)

        # Entity memories (stub)
        entity_memories: list[EntityMemoryDTO] = []

        # Related topics (stub)
        related_topics: list[int] = []

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

    @classmethod
    def from_uow(cls, uow: "UnitOfWork") -> "MemoryService":
        """Create MemoryService from UnitOfWork.

        Args:
            uow: Unit of work with repositories.

        Returns:
            Configured MemoryService.
        """
        from app.storage.uow import UnitOfWork

        return cls(
            topic_memory_repo=uow.topic_memories,
            entity_memory_repo=uow.entity_memories,
            judgement_repo=uow.judgements,
            timeline_repo=None,  # Will be added in Week 10
        )
