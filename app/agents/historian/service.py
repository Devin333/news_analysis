"""Historian Service.

Provides high-level interface for running historical analysis on topics.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from app.agents.historian.agent import HistorianAgent
from app.agents.historian.input_builder import HistorianInputBuilder
from app.agents.historian.schemas import HistorianInput, HistorianOutput
from app.agents.base import AgentConfig
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO
    from app.memory.retrieval.service import MemoryRetrievalService
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class HistorianService:
    """Service for running Historian Agent on topics.

    Coordinates:
    - Gathering historical context
    - Building agent input
    - Running the agent
    - Processing results
    """

    def __init__(
        self,
        retrieval_service: "MemoryRetrievalService | None" = None,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            retrieval_service: Memory retrieval service.
            uow: Unit of work for database access.
        """
        self._retrieval_service = retrieval_service
        self._uow = uow
        self._input_builder = HistorianInputBuilder()
        self._agent: HistorianAgent | None = None

    def _get_agent(self) -> HistorianAgent:
        """Get or create the Historian agent."""
        if self._agent is None:
            config = AgentConfig(
                max_steps=8,
                temperature=0.3,
                enable_tools=True,
                prompt_version="v1",
            )
            self._agent = HistorianAgent(
                config=config,
                retrieval_service=self._retrieval_service,
            )
        return self._agent

    async def run_for_topic(
        self,
        topic_id: int,
    ) -> tuple[HistorianOutput | None, dict]:
        """Run historical analysis for a topic.

        Args:
            topic_id: ID of the topic to analyze.

        Returns:
            Tuple of (HistorianOutput or None, metadata dict).
        """
        start_time = datetime.utcnow()
        metadata = {
            "topic_id": topic_id,
            "started_at": start_time.isoformat(),
            "success": False,
        }

        try:
            # Get topic
            topic = await self._get_topic(topic_id)
            if topic is None:
                metadata["error"] = f"Topic {topic_id} not found"
                return None, metadata

            # Get historical context
            history_context = None
            if self._retrieval_service:
                history_context = await self._retrieval_service.retrieve_topic_history(
                    topic_id
                )

            # Get representative item
            representative_item = await self._get_representative_item(topic_id)

            # Get recent items
            recent_items = await self._get_recent_items(topic_id)

            # Get entity names
            entity_names = await self._get_entity_names(topic_id)

            # Build input
            historian_input = self._input_builder.build(
                topic=topic,
                history_context=history_context,
                representative_item=representative_item,
                recent_items=recent_items,
                entity_names=entity_names,
            )

            # Run agent
            agent = self._get_agent()
            output, run_result = await agent.analyze_topic(historian_input)

            # Update metadata
            end_time = datetime.utcnow()
            metadata.update({
                "success": output is not None,
                "completed_at": end_time.isoformat(),
                "duration_ms": (end_time - start_time).total_seconds() * 1000,
                "total_steps": run_result.total_steps if run_result else 0,
                "run_status": run_result.status if run_result else "unknown",
            })

            if output:
                logger.info(
                    f"Historian analysis completed for topic {topic_id}: "
                    f"status={output.historical_status}, "
                    f"confidence={output.historical_confidence:.2f}"
                )
            else:
                logger.warning(f"Historian analysis failed for topic {topic_id}")

            return output, metadata

        except Exception as e:
            logger.error(f"Error running historian for topic {topic_id}: {e}")
            metadata["error"] = str(e)
            return None, metadata

    async def run_for_item(
        self,
        item_id: int,
        topic_id: int,
    ) -> tuple[HistorianOutput | None, dict]:
        """Run historical analysis for a specific item within a topic.

        Args:
            item_id: ID of the item to focus on.
            topic_id: ID of the topic.

        Returns:
            Tuple of (HistorianOutput or None, metadata dict).
        """
        # For now, delegate to topic-level analysis
        # In future, could add item-specific context
        return await self.run_for_topic(topic_id)

    async def _get_topic(self, topic_id: int) -> "TopicReadDTO | None":
        """Get topic by ID."""
        if self._uow is None:
            return None

        async with self._uow:
            topic = await self._uow.topics.get_by_id(topic_id)
            if topic is None:
                return None

            # Convert to DTO
            from app.contracts.dto.topic import TopicReadDTO

            return TopicReadDTO(
                id=topic.id,
                title=topic.title,
                summary=topic.summary,
                board_type=topic.board_type,
                item_count=topic.item_count,
                source_count=topic.source_count,
                heat_score=topic.heat_score,
                trend_score=topic.trend_score,
                first_seen_at=topic.first_seen_at,
                last_seen_at=topic.last_seen_at,
                created_at=topic.created_at,
                updated_at=topic.updated_at,
            )

    async def _get_representative_item(self, topic_id: int):
        """Get representative item for topic."""
        if self._uow is None:
            return None

        async with self._uow:
            # Get topic item IDs
            item_ids = await self._uow.topics.get_topic_items(topic_id, limit=1)
            if not item_ids:
                return None

            # Get the actual item
            item = await self._uow.normalized_items.get_by_id(item_ids[0])
            if item is None:
                return None

            return item

    async def _get_recent_items(self, topic_id: int, limit: int = 10):
        """Get recent items for topic."""
        if self._uow is None:
            return []

        async with self._uow:
            # Get topic item IDs
            item_ids = await self._uow.topics.get_topic_items(topic_id, limit=limit)
            if not item_ids:
                return []

            # Get actual items
            items = []
            for item_id in item_ids:
                item = await self._uow.normalized_items.get_by_id(item_id)
                if item:
                    items.append(item)

            return items

    async def _get_entity_names(self, topic_id: int) -> list[str]:
        """Get entity names related to topic."""
        if self._uow is None:
            return []

        # TODO: Implement entity retrieval
        return []
