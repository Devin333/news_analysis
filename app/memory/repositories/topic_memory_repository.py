"""Topic Memory Repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import (
    TopicMemoryCreateDTO,
    TopicMemoryDTO,
    TopicSnapshotCreateDTO,
    TopicSnapshotDTO,
)
from app.storage.db.models.topic_memory import TopicMemory
from app.storage.db.models.topic_snapshot import TopicSnapshot

logger = get_logger(__name__)


class TopicMemoryRepository:
    """Repository for topic memory operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def get_by_topic_id(self, topic_id: int) -> TopicMemoryDTO | None:
        """Get topic memory by topic ID.

        Args:
            topic_id: The topic ID.

        Returns:
            TopicMemoryDTO if found, None otherwise.
        """
        stmt = select(TopicMemory).where(TopicMemory.topic_id == topic_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._to_dto(row)

    async def create(self, data: TopicMemoryCreateDTO) -> TopicMemoryDTO:
        """Create a new topic memory.

        Args:
            data: Topic memory creation data.

        Returns:
            Created TopicMemoryDTO.
        """
        now = datetime.now(timezone.utc)
        model = TopicMemory(
            topic_id=data.topic_id,
            first_seen_at=data.first_seen_at,
            last_seen_at=now,
            historical_status=data.historical_status,
            current_stage=data.current_stage,
            history_summary=data.history_summary,
            key_milestones_json=[],
            last_refreshed_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created topic memory for topic {data.topic_id}")
        return self._to_dto(model)

    async def update(
        self,
        topic_id: int,
        data: dict[str, Any],
    ) -> TopicMemoryDTO | None:
        """Update topic memory.

        Args:
            topic_id: The topic ID.
            data: Fields to update.

        Returns:
            Updated TopicMemoryDTO if found, None otherwise.
        """
        stmt = select(TopicMemory).where(TopicMemory.topic_id == topic_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(model, key):
                setattr(model, key, value)
            elif key == "key_milestones" and hasattr(model, "key_milestones_json"):
                model.key_milestones_json = value
            elif key == "metadata" and hasattr(model, "metadata_json"):
                model.metadata_json = value

        model.last_refreshed_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Updated topic memory for topic {topic_id}")
        return self._to_dto(model)

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
        now = datetime.now(timezone.utc)
        model = TopicSnapshot(
            topic_id=data.topic_id,
            snapshot_at=now,
            summary=data.summary,
            why_it_matters=data.why_it_matters,
            system_judgement=data.system_judgement,
            heat_score=data.heat_score,
            trend_score=data.trend_score,
            item_count=data.item_count,
            source_count=data.source_count,
            representative_item_id=data.representative_item_id,
            timeline_json=[],
            metadata_json={},
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created snapshot for topic {data.topic_id}")
        return self._snapshot_to_dto(model)

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
            List of TopicSnapshotDTO ordered by snapshot_at desc.
        """
        stmt = (
            select(TopicSnapshot)
            .where(TopicSnapshot.topic_id == topic_id)
            .order_by(TopicSnapshot.snapshot_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [self._snapshot_to_dto(row) for row in rows]

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
        stmt = (
            select(TopicSnapshot)
            .where(TopicSnapshot.topic_id == topic_id)
            .order_by(TopicSnapshot.snapshot_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return self._snapshot_to_dto(row)

    def _to_dto(self, model: TopicMemory) -> TopicMemoryDTO:
        """Convert ORM model to DTO."""
        return TopicMemoryDTO(
            id=model.id,
            topic_id=model.topic_id,
            first_seen_at=model.first_seen_at,
            last_seen_at=model.last_seen_at,
            historical_status=model.historical_status,
            current_stage=model.current_stage,
            history_summary=model.history_summary,
            key_milestones=model.key_milestones_json or [],
            last_refreshed_at=model.last_refreshed_at,
            metadata=model.metadata_json or {},
        )

    def _snapshot_to_dto(self, model: TopicSnapshot) -> TopicSnapshotDTO:
        """Convert snapshot ORM model to DTO."""
        return TopicSnapshotDTO(
            id=model.id,
            topic_id=model.topic_id,
            snapshot_at=model.snapshot_at,
            summary=model.summary,
            why_it_matters=model.why_it_matters,
            system_judgement=model.system_judgement,
            heat_score=float(model.heat_score),
            trend_score=float(model.trend_score),
            item_count=model.item_count,
            source_count=model.source_count,
            representative_item_id=model.representative_item_id,
            timeline_json=model.timeline_json or [],
            metadata=model.metadata_json or {},
        )
