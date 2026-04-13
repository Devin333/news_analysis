"""Analyst Service.

Provides high-level interface for running value analysis on topics.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.agents.analyst.agent import AnalystAgent
from app.agents.analyst.input_builder import AnalystInputBuilder
from app.agents.analyst.schemas import AnalystInput, AnalystOutput
from app.agents.base import AgentConfig
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agents.historian.schemas import HistorianOutput
    from app.contracts.dto.topic import TopicReadDTO
    from app.memory.retrieval.service import MemoryRetrievalService
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class AnalystService:
    """Service for running Analyst Agent on topics.

    Coordinates:
    - Gathering context
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
        self._input_builder = AnalystInputBuilder()
        self._agent: AnalystAgent | None = None

    def _get_agent(self) -> AnalystAgent:
        """Get or create the Analyst agent."""
        if self._agent is None:
            config = AgentConfig(
                max_steps=6,
                temperature=0.4,
                enable_tools=True,
                prompt_version="v1",
            )
            self._agent = AnalystAgent(
                config=config,
                retrieval_service=self._retrieval_service,
            )
        return self._agent

    async def run_for_topic(
        self,
        topic_id: int,
        historian_output: "HistorianOutput | None" = None,
    ) -> tuple[AnalystOutput | None, dict]:
        """Run value analysis for a topic.

        Args:
            topic_id: ID of the topic to analyze.
            historian_output: Optional historian output for context.

        Returns:
            Tuple of (AnalystOutput or None, metadata dict).
        """
        start_time = datetime.utcnow()
        metadata: dict[str, Any] = {
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

            # Get representative item
            representative_item = await self._get_representative_item(topic_id)

            # Get recent items
            recent_items = await self._get_recent_items(topic_id)

            # Get tags
            tags = await self._get_tags(topic_id)

            # Get entity names
            entity_names = await self._get_entity_names(topic_id)

            # Get recent judgements
            recent_judgements = await self._get_recent_judgements(topic_id)

            # Build input
            analyst_input = self._input_builder.build(
                topic=topic,
                historian_output=historian_output,
                representative_item=representative_item,
                recent_items=recent_items,
                tags=tags,
                entity_names=entity_names,
                recent_judgements=recent_judgements,
            )

            # Run agent
            agent = self._get_agent()
            output, run_result = await agent.analyze_topic(analyst_input)

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
                    f"Analyst completed for topic {topic_id}: "
                    f"trend={output.trend_stage}, "
                    f"confidence={output.confidence:.2f}"
                )
            else:
                logger.warning(f"Analyst failed for topic {topic_id}")

            return output, metadata

        except Exception as e:
            logger.error(f"Error running analyst for topic {topic_id}: {e}")
            metadata["error"] = str(e)
            return None, metadata

    async def _get_topic(self, topic_id: int) -> "TopicReadDTO | None":
        """Get topic by ID."""
        if self._uow is None:
            return None

        async with self._uow:
            return await self._uow.topics.get_by_id(topic_id)

    async def _get_representative_item(self, topic_id: int):
        """Get representative item for topic."""
        if self._uow is None:
            return None

        async with self._uow:
            item_ids = await self._uow.topics.get_topic_items(topic_id, limit=1)
            if not item_ids:
                return None
            return await self._uow.normalized_items.get_by_id(item_ids[0])

    async def _get_recent_items(self, topic_id: int, limit: int = 10):
        """Get recent items for topic."""
        if self._uow is None:
            return []

        async with self._uow:
            item_ids = await self._uow.topics.get_topic_items(topic_id, limit=limit)
            if not item_ids:
                return []

            items = []
            for item_id in item_ids:
                item = await self._uow.normalized_items.get_by_id(item_id)
                if item:
                    items.append(item)
            return items

    async def _get_tags(self, topic_id: int) -> list[str]:
        """Get tags for topic."""
        if self._retrieval_service:
            try:
                return await self._retrieval_service.retrieve_topic_tags(topic_id)
            except Exception:
                pass
        return []

    async def _get_entity_names(self, topic_id: int) -> list[str]:
        """Get entity names related to topic."""
        # TODO: Implement entity retrieval
        return []

    async def _get_recent_judgements(self, topic_id: int) -> list[dict]:
        """Get recent judgements for topic."""
        if self._uow is None:
            return []

        try:
            async with self._uow:
                judgements = await self._uow.judgements.list_by_target(
                    "topic", topic_id, limit=5
                )
                return [
                    {
                        "agent_name": j.agent_name,
                        "judgement_type": j.judgement_type,
                        "judgement": j.judgement,
                        "confidence": j.confidence,
                        "created_at": j.created_at.isoformat(),
                    }
                    for j in judgements
                ]
        except Exception:
            return []
