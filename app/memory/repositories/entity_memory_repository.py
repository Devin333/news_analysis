"""Entity Memory Repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import EntityMemoryCreateDTO, EntityMemoryDTO
from app.storage.db.models.entity import Entity
from app.storage.db.models.entity_memory import EntityMemory
from app.storage.db.models.topic_entity import TopicEntity

logger = get_logger(__name__)


class EntityMemoryRepository:
    """Repository for entity memory operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_entity_id(self, entity_id: int) -> EntityMemoryDTO | None:
        """Get entity memory by entity ID.

        Args:
            entity_id: The entity ID.

        Returns:
            EntityMemoryDTO if found, None otherwise.
        """
        stmt = select(EntityMemory).where(EntityMemory.entity_id == entity_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._to_dto(row)

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
        stmt = select(EntityMemory).where(EntityMemory.entity_id == data.entity_id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing:
            # Update
            if data.summary is not None:
                existing.summary = data.summary
            existing.last_refreshed_at = now
            await self._session.flush()
            await self._session.refresh(existing)
            logger.info(f"Updated entity memory for entity {data.entity_id}")
            return self._to_dto(existing)
        else:
            # Create
            model = EntityMemory(
                entity_id=data.entity_id,
                summary=data.summary,
                related_topic_ids_json=[],
                milestones_json=[],
                recent_signals_json=[],
                last_refreshed_at=now,
            )
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            logger.info(f"Created entity memory for entity {data.entity_id}")
            return self._to_dto(model)

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
        stmt = (
            select(TopicEntity.topic_id)
            .where(TopicEntity.entity_id == entity_id)
            .order_by(TopicEntity.relevance_score.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

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
        # Check if already exists
        stmt = select(TopicEntity).where(
            TopicEntity.topic_id == topic_id,
            TopicEntity.entity_id == entity_id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update relevance score
            existing.relevance_score = relevance_score
        else:
            # Create new relationship
            model = TopicEntity(
                topic_id=topic_id,
                entity_id=entity_id,
                relevance_score=relevance_score,
            )
            self._session.add(model)

        await self._session.flush()
        logger.info(f"Attached entity {entity_id} to topic {topic_id}")

    async def get_entity_by_normalized_name(
        self,
        normalized_name: str,
        entity_type: str | None = None,
    ) -> Entity | None:
        """Get entity by normalized name.

        Args:
            normalized_name: Normalized entity name.
            entity_type: Optional entity type filter.

        Returns:
            Entity if found, None otherwise.
        """
        stmt = select(Entity).where(Entity.normalized_name == normalized_name)
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_entity(
        self,
        entity_type: str,
        name: str,
        normalized_name: str,
        description: str | None = None,
    ) -> Entity:
        """Create a new entity.

        Args:
            entity_type: Type of entity.
            name: Entity name.
            normalized_name: Normalized name for matching.
            description: Optional description.

        Returns:
            Created Entity.
        """
        now = datetime.now(timezone.utc)
        model = Entity(
            entity_type=entity_type,
            name=name,
            normalized_name=normalized_name,
            description=description,
            first_seen_at=now,
            last_seen_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        logger.info(f"Created entity: {name} ({entity_type})")
        return model

    def _to_dto(self, model: EntityMemory) -> EntityMemoryDTO:
        """Convert ORM model to DTO."""
        return EntityMemoryDTO(
            id=model.id,
            entity_id=model.entity_id,
            summary=model.summary,
            related_topic_ids=model.related_topic_ids_json or [],
            milestones=model.milestones_json or [],
            recent_signals=model.recent_signals_json or [],
            last_refreshed_at=model.last_refreshed_at,
            metadata=model.metadata_json or {},
        )
