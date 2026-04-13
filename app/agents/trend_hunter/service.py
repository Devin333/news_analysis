"""TrendHunter service.

Provides high-level methods for trend analysis.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from app.agents.trend_hunter.agent import TrendHunterAgent
from app.agents.trend_hunter.input_builder import TrendHunterInputBuilder
from app.agents.trend_hunter.schemas import TrendHunterOutput
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class TrendHunterService:
    """Service for trend analysis.

    Provides methods for analyzing topics for trends.
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
        """
        self._uow = uow
        self._input_builder = TrendHunterInputBuilder()
        self._agent = TrendHunterAgent()

    async def run_for_topic(
        self,
        topic_id: int,
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[TrendHunterOutput | None, dict[str, Any]]:
        """Analyze a topic for trends.

        Args:
            topic_id: ID of the topic.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (TrendHunterOutput or None, metadata).
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            return None, {"error": "Topic not found"}

        tags = await self._get_topic_tags(topic_id)
        metrics = await self._compute_trend_metrics(topic_id)

        trend_input = self._input_builder.build_input(
            topic=topic,
            metrics=metrics,
            historian_output=historian_output,
            analyst_output=analyst_output,
            tags=tags,
        )

        output, meta = await self._agent.analyze_trend(trend_input)
        return output, meta or {}

    async def scan_recent_topics(
        self,
        *,
        window_days: int = 7,
        min_items: int = 3,
        limit: int = 50,
    ) -> list[tuple[int, TrendHunterOutput]]:
        """Scan recent topics for trends.

        Args:
            window_days: Days to look back.
            min_items: Minimum items to consider.
            limit: Maximum topics to scan.

        Returns:
            List of (topic_id, TrendHunterOutput) tuples.
        """
        # Get recent active topics
        topic_ids = await self._get_recent_active_topics(
            window_days=window_days,
            min_items=min_items,
            limit=limit,
        )

        results = []
        for topic_id in topic_ids:
            output, _ = await self.run_for_topic(topic_id)
            if output and output.is_emerging:
                results.append((topic_id, output))

        # Sort by confidence
        results.sort(key=lambda x: x[1].confidence, reverse=True)
        return results

    async def _get_topic(self, topic_id: int) -> "TopicReadDTO | None":
        """Get topic by ID."""
        if self._uow is None or self._uow.topics is None:
            return None
        return await self._uow.topics.get_by_id(topic_id)

    async def _get_topic_tags(self, topic_id: int) -> list[str]:
        """Get tags for a topic."""
        return []

    async def _compute_trend_metrics(self, topic_id: int) -> dict[str, Any]:
        """Compute trend metrics for a topic."""
        # Stub - would compute actual metrics
        return {
            "item_count_7d": 0,
            "item_count_30d": 0,
            "source_count_7d": 0,
            "source_count_30d": 0,
            "growth_rate_7d": 0.0,
            "growth_rate_30d": 0.0,
            "items_last_24h": 0,
            "items_last_7d": 0,
            "unique_sources_7d": 0,
            "source_diversity_score": 0.0,
            "has_recent_release": False,
            "has_discussion_spike": False,
            "related_entity_activity": [],
        }

    async def _get_recent_active_topics(
        self,
        *,
        window_days: int = 7,
        min_items: int = 3,
        limit: int = 50,
    ) -> list[int]:
        """Get recent active topic IDs."""
        # Stub - would query database
        return []
