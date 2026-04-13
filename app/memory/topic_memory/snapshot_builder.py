"""Topic Snapshot Builder for creating point-in-time topic snapshots."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TopicSnapshotCreateDTO
from app.contracts.dto.topic import TopicReadDTO

if TYPE_CHECKING:
    from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
    from app.storage.repositories.tag_repository import TagRepository
    from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class TopicSnapshotBuilder:
    """Builder for creating topic snapshots.

    Collects current topic state and creates a snapshot for
    historical tracking.
    """

    def __init__(
        self,
        topic_repo: "TopicRepository",
        item_repo: "NormalizedItemRepository",
        tag_repo: "TagRepository | None" = None,
    ) -> None:
        """Initialize the builder.

        Args:
            topic_repo: Topic repository.
            item_repo: Normalized item repository.
            tag_repo: Optional tag repository.
        """
        self._topic_repo = topic_repo
        self._item_repo = item_repo
        self._tag_repo = tag_repo

    async def build_snapshot(
        self,
        topic_id: int,
        include_judgement: bool = True,
    ) -> TopicSnapshotCreateDTO | None:
        """Build a snapshot for a topic.

        Collects:
        - summary
        - representative item
        - item_count
        - source_count
        - heat_score
        - trend_score
        - existing judgment (if any)

        Args:
            topic_id: The topic ID.
            include_judgement: Whether to include existing judgement.

        Returns:
            TopicSnapshotCreateDTO or None if topic not found.
        """
        # Get topic
        topic = await self._topic_repo.get_by_id(topic_id)
        if topic is None:
            logger.warning(f"Topic {topic_id} not found for snapshot")
            return None

        # Get representative item summary if exists
        why_it_matters: str | None = None
        if topic.representative_item_id:
            item = await self._item_repo.get_by_id(topic.representative_item_id)
            if item and item.summary:
                why_it_matters = item.summary

        # Build snapshot
        snapshot = TopicSnapshotCreateDTO(
            topic_id=topic_id,
            summary=topic.summary,
            why_it_matters=why_it_matters,
            system_judgement=None,  # Will be filled by Analyst later
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
            item_count=topic.item_count,
            source_count=topic.source_count,
            representative_item_id=topic.representative_item_id,
        )

        logger.info(f"Built snapshot for topic {topic_id}")
        return snapshot

    async def build_snapshot_from_dto(
        self,
        topic: TopicReadDTO,
        why_it_matters: str | None = None,
        system_judgement: str | None = None,
    ) -> TopicSnapshotCreateDTO:
        """Build a snapshot from a TopicReadDTO.

        Args:
            topic: Topic DTO.
            why_it_matters: Optional importance explanation.
            system_judgement: Optional system judgement.

        Returns:
            TopicSnapshotCreateDTO.
        """
        return TopicSnapshotCreateDTO(
            topic_id=topic.id,
            summary=topic.summary,
            why_it_matters=why_it_matters,
            system_judgement=system_judgement,
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
            item_count=topic.item_count,
            source_count=topic.source_count,
            representative_item_id=topic.representative_item_id,
        )

    async def build_batch_snapshots(
        self,
        topic_ids: list[int],
    ) -> list[TopicSnapshotCreateDTO]:
        """Build snapshots for multiple topics.

        Args:
            topic_ids: List of topic IDs.

        Returns:
            List of TopicSnapshotCreateDTO.
        """
        snapshots = []
        for topic_id in topic_ids:
            snapshot = await self.build_snapshot(topic_id)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots
