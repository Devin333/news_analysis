"""Topic service for managing topic lifecycle."""

from datetime import datetime, timezone

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import (
    TopicCreateDTO,
    TopicReadDTO,
    TopicSummaryDTO,
)
from app.storage.repositories.normalized_item_repository import NormalizedItemRepository
from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


class TopicService:
    """Service for topic domain operations."""

    def __init__(
        self,
        topic_repo: TopicRepository,
        item_repo: NormalizedItemRepository,
    ) -> None:
        self._topic_repo = topic_repo
        self._item_repo = item_repo

    async def create_topic_from_item(
        self,
        item: NormalizedItemDTO,
        *,
        topic_type: str = "auto",
    ) -> TopicReadDTO:
        """Create a new topic from a normalized item.

        Args:
            item: The normalized item to create topic from.
            topic_type: Type of topic (auto, manual, etc.).

        Returns:
            The created topic.
        """
        board_type = item.board_type_candidate or BoardType.GENERAL

        create_dto = TopicCreateDTO(
            board_type=board_type,
            topic_type=topic_type,
            title=item.title,
            summary=item.excerpt,
            representative_item_id=item.id,
            metadata_json={
                "created_from_item_id": item.id,
                "initial_source_id": item.source_id,
            },
        )

        topic = await self._topic_repo.create(create_dto)
        logger.info(f"Created topic '{topic.title}' (id={topic.id}) from item {item.id}")

        # Link the item to the topic
        if item.id is not None:
            await self._topic_repo.add_item(
                topic.id,
                item.id,
                link_reason="initial_item",
            )
            # Update metrics
            await self._topic_repo.update_metrics(
                topic.id,
                item_count=1,
                source_count=1,
            )

        return topic

    async def add_item_to_topic(
        self,
        topic_id: int,
        item: NormalizedItemDTO,
        *,
        link_reason: str | None = None,
    ) -> bool:
        """Add an item to an existing topic.

        Args:
            topic_id: The topic ID to add item to.
            item: The normalized item to add.
            link_reason: Reason for linking (e.g., "similarity", "manual").

        Returns:
            True if successful.
        """
        if item.id is None:
            logger.warning("Cannot add item without ID to topic")
            return False

        # Add the item link
        await self._topic_repo.add_item(topic_id, item.id, link_reason=link_reason)

        # Update topic metrics
        await self.update_topic_metrics(topic_id)

        logger.info(f"Added item {item.id} to topic {topic_id}")
        return True

    async def update_topic_metrics(self, topic_id: int) -> bool:
        """Update topic metrics based on linked items.

        Args:
            topic_id: The topic ID to update.

        Returns:
            True if successful.
        """
        # Count items
        item_count = await self._topic_repo.count_items(topic_id)

        # Get item IDs to count unique sources
        item_ids = await self._topic_repo.get_topic_items(topic_id)

        # For now, estimate source_count as item_count (will improve later)
        # TODO: Query actual unique source count from items
        source_count = min(item_count, 10)  # Placeholder

        # Calculate heat score based on item count and recency
        heat_score = self._calculate_heat_score(item_count)

        # Update metrics
        success = await self._topic_repo.update_metrics(
            topic_id,
            item_count=item_count,
            source_count=source_count,
            heat_score=heat_score,
            last_seen_at=datetime.now(timezone.utc),
        )

        logger.debug(f"Updated metrics for topic {topic_id}: items={item_count}, heat={heat_score}")
        return success

    async def recompute_representative_item(self, topic_id: int) -> int | None:
        """Recompute and update the representative item for a topic.

        The representative item is selected based on:
        - Recency (newer is better)
        - Source trust score (higher is better)
        - Content quality (longer, more informative)

        Args:
            topic_id: The topic ID.

        Returns:
            The selected representative item ID, or None if no items.
        """
        item_ids = await self._topic_repo.get_topic_items(topic_id, limit=50)
        if not item_ids:
            return None

        # For now, use the most recent item as representative
        # TODO: Implement proper scoring based on trust/quality
        representative_id = item_ids[0]

        # Update topic
        await self._topic_repo.update_summary(
            topic_id,
            summary=None,  # Keep existing summary
            representative_item_id=representative_id,
        )

        logger.info(f"Set representative item {representative_id} for topic {topic_id}")
        return representative_id

    async def build_topic_summary_stub(self, topic_id: int) -> str:
        """Build a basic summary stub for a topic.

        This creates a simple summary without LLM, based on:
        - Topic title
        - Item count
        - Time range
        - Source diversity

        Args:
            topic_id: The topic ID.

        Returns:
            A summary stub string.
        """
        topic = await self._topic_repo.get_by_id(topic_id)
        if topic is None:
            return ""

        item_count = topic.item_count
        source_count = topic.source_count

        # Build stub
        parts = [topic.title]

        if item_count > 1:
            parts.append(f"({item_count} 条相关内容")
            if source_count > 1:
                parts.append(f"来自 {source_count} 个来源)")
            else:
                parts.append(")")

        summary_stub = " ".join(parts)

        # Update topic summary
        await self._topic_repo.update_summary(topic_id, summary_stub)

        logger.debug(f"Built summary stub for topic {topic_id}: {summary_stub[:50]}...")
        return summary_stub

    async def get_topic(self, topic_id: int) -> TopicReadDTO | None:
        """Get topic by ID."""
        return await self._topic_repo.get_by_id(topic_id)

    async def list_recent_topics(self, *, limit: int = 100) -> list[TopicReadDTO]:
        """List recent topics."""
        return await self._topic_repo.list_recent(limit=limit)

    async def list_topic_summaries(self, *, limit: int = 100) -> list[TopicSummaryDTO]:
        """List recent topic summaries (lightweight)."""
        return await self._topic_repo.list_recent_summaries(limit=limit)

    async def list_topics_by_board(
        self,
        board_type: BoardType,
        *,
        limit: int = 100,
    ) -> list[TopicReadDTO]:
        """List topics by board type."""
        return await self._topic_repo.list_by_board(board_type, limit=limit)

    async def get_topic_items(self, topic_id: int, *, limit: int = 100) -> list[int]:
        """Get item IDs for a topic."""
        return await self._topic_repo.get_topic_items(topic_id, limit=limit)

    async def resolve_topic_for_item(
        self,
        item: NormalizedItemDTO,
    ) -> TopicReadDTO:
        """Resolve which topic an item should belong to.

        This method determines whether to merge the item into an existing
        topic or create a new topic for it.

        Args:
            item: The normalized item to process.

        Returns:
            The topic (existing or newly created) for the item.
        """
        from app.processing.clustering.merge_service import MergeAction, MergeService

        # Create merge service
        merge_service = MergeService(
            self._topic_repo,
            policy_name="default",
            use_embedding=False,
        )

        # Get merge decision
        result = await merge_service.resolve_for_item(item)

        if result.action == MergeAction.MERGE_INTO and result.target_topic_id:
            # Merge into existing topic
            topic = await self._topic_repo.get_by_id(result.target_topic_id)
            if topic:
                await self.add_item_to_topic(
                    result.target_topic_id,
                    item,
                    link_reason=f"merge:{result.rationale[:50]}",
                )
                logger.info(
                    f"Merged item '{item.title[:50]}...' into topic {result.target_topic_id}"
                )
                return topic

        # Create new topic
        topic = await self.create_topic_from_item(item)
        logger.info(f"Created new topic {topic.id} for item '{item.title[:50]}...'")
        return topic

    async def refresh_topic_tags(
        self,
        topic_id: int,
        *,
        tag_repo: "TagRepository | None" = None,
    ) -> list["TopicTagDTO"]:
        """Refresh tags for a topic by aggregating item tags.

        Args:
            topic_id: The topic ID.
            tag_repo: Optional tag repository (for persistence).

        Returns:
            List of aggregated topic tags.
        """
        from app.contracts.dto.tag import TopicTagDTO
        from app.processing.tagging.tag_service import get_tag_service
        from app.processing.tagging.topic_tag_aggregator import (
            ItemTagInfo,
            get_topic_tag_aggregator,
        )

        # Get topic items
        item_ids = await self._topic_repo.get_topic_items(topic_id, limit=200)
        if not item_ids:
            logger.warning(f"No items found for topic {topic_id}")
            return []

        # Get items and tag them
        tag_service = get_tag_service()
        aggregator = get_topic_tag_aggregator()

        item_tags: list[list[ItemTagInfo]] = []

        for item_id in item_ids:
            item = await self._item_repo.get_by_id(item_id)
            if item is None:
                continue

            # Tag the item
            result = tag_service.tag_item(item)
            if not result.success:
                continue

            # Convert to ItemTagInfo
            tags = [
                ItemTagInfo(
                    tag_name=t.tag_name,
                    tag_type=t.tag_type,
                    confidence=t.confidence,
                    source_trust=1.0,  # TODO: Get from source
                    published_at=item.published_at,
                    item_id=item.id,
                )
                for t in result.tags
            ]
            item_tags.append(tags)

        # Aggregate tags
        agg_result = aggregator.aggregate(topic_id, item_tags)

        # Persist if repository provided
        if tag_repo and agg_result.tags:
            await tag_repo.replace_topic_tags(topic_id, agg_result.tags)
            logger.info(f"Persisted {len(agg_result.tags)} tags for topic {topic_id}")

        return agg_result.tags

    def _calculate_heat_score(self, item_count: int) -> float:
        """Calculate heat score based on item count.

        Simple formula for now:
        - Base score from item count (log scale)
        - Max score capped at 100

        Args:
            item_count: Number of items in topic.

        Returns:
            Heat score between 0 and 100.
        """
        import math

        if item_count <= 0:
            return 0.0

        # Log scale: 1 item = ~10, 10 items = ~33, 100 items = ~66
        score = math.log10(item_count + 1) * 33.0
        return min(score, 100.0)

    async def refresh_topic_snapshot(
        self,
        topic_id: int,
        *,
        memory_service: "MemoryService | None" = None,
    ) -> "TopicSnapshotDTO | None":
        """Create a new snapshot for a topic.

        Args:
            topic_id: The topic ID.
            memory_service: Optional memory service for persistence.

        Returns:
            Created TopicSnapshotDTO or None if failed.
        """
        from app.contracts.dto.memory import TopicSnapshotDTO
        from app.memory.topic_memory.snapshot_builder import TopicSnapshotBuilder

        # Build snapshot
        builder = TopicSnapshotBuilder(
            topic_repo=self._topic_repo,
            item_repo=self._item_repo,
        )
        snapshot_data = await builder.build_snapshot(topic_id)

        if snapshot_data is None:
            logger.warning(f"Failed to build snapshot for topic {topic_id}")
            return None

        # Persist if memory service provided
        if memory_service:
            snapshot = await memory_service.create_topic_snapshot(topic_id, snapshot_data)
            if snapshot:
                logger.info(f"Created and persisted snapshot for topic {topic_id}")
                return snapshot

        # Return as DTO without persistence
        from datetime import datetime, timezone

        return TopicSnapshotDTO(
            topic_id=topic_id,
            snapshot_at=datetime.now(timezone.utc),
            summary=snapshot_data.summary,
            why_it_matters=snapshot_data.why_it_matters,
            system_judgement=snapshot_data.system_judgement,
            heat_score=snapshot_data.heat_score,
            trend_score=snapshot_data.trend_score,
            item_count=snapshot_data.item_count,
            source_count=snapshot_data.source_count,
            representative_item_id=snapshot_data.representative_item_id,
        )


    async def refresh_topic_historical_context(
        self,
        topic_id: int,
        *,
        historian_service: "HistorianService | None" = None,
        topic_memory_service: "TopicMemoryService | None" = None,
    ) -> "HistorianOutput | None":
        """Run historian analysis and save results.

        Args:
            topic_id: The topic ID.
            historian_service: Historian service for analysis.
            topic_memory_service: Topic memory service for persistence.

        Returns:
            HistorianOutput or None if failed.
        """
        if historian_service is None:
            logger.warning("No historian service provided")
            return None

        # Run historian analysis
        output, metadata = await historian_service.run_for_topic(topic_id)

        if output is None:
            logger.warning(f"Historian analysis failed for topic {topic_id}")
            return None

        # Save to topic memory
        if topic_memory_service:
            saved = await topic_memory_service.update_from_historian(topic_id, output)
            if saved:
                logger.info(f"Saved historian output for topic {topic_id}")
            else:
                logger.warning(f"Failed to save historian output for topic {topic_id}")

        return output


# Type hints for lazy imports
if False:  # TYPE_CHECKING
    from app.agents.historian.schemas import HistorianOutput
    from app.agents.historian.service import HistorianService
    from app.contracts.dto.memory import TopicSnapshotDTO
    from app.contracts.dto.tag import TopicTagDTO
    from app.memory.service import MemoryService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.repositories.tag_repository import TagRepository
