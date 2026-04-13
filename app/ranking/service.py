"""Ranking service for scoring and ordering topics."""

from datetime import datetime, timezone
from typing import Any

from app.contracts.dto.ranking import (
    RankedTopicDTO,
    RankingContextDTO,
    RankingFeatureDTO,
    RankingScoreDTO,
)
from app.contracts.protocols.ranking import (
    RankingFeatureProviderProtocol,
    RankingStrategyProtocol,
)


class RankingService:
    """Service for ranking topics across different contexts.

    Coordinates feature extraction and strategy application.
    """

    def __init__(
        self,
        feature_provider: RankingFeatureProviderProtocol,
        strategies: dict[str, RankingStrategyProtocol] | None = None,
    ) -> None:
        """Initialize ranking service.

        Args:
            feature_provider: Provider for extracting ranking features
            strategies: Dict mapping context names to strategies
        """
        self._feature_provider = feature_provider
        self._strategies: dict[str, RankingStrategyProtocol] = strategies or {}
        self._default_strategy: RankingStrategyProtocol | None = None

    def register_strategy(
        self,
        context_name: str,
        strategy: RankingStrategyProtocol,
        is_default: bool = False,
    ) -> None:
        """Register a ranking strategy for a context.

        Args:
            context_name: Name of the context (e.g., "news_feed")
            strategy: The strategy implementation
            is_default: Whether this is the default strategy
        """
        self._strategies[context_name] = strategy
        if is_default:
            self._default_strategy = strategy

    def get_strategy(self, context_name: str) -> RankingStrategyProtocol | None:
        """Get strategy for a context.

        Args:
            context_name: Name of the context

        Returns:
            Strategy if found, else default strategy, else None
        """
        return self._strategies.get(context_name, self._default_strategy)

    async def score_topic(
        self,
        topic_id: int,
        context: RankingContextDTO,
    ) -> RankingScoreDTO:
        """Score a single topic.

        Args:
            topic_id: The topic to score
            context: Ranking context

        Returns:
            RankingScoreDTO with score and breakdown
        """
        strategy = self.get_strategy(context.context_name)
        if not strategy:
            return RankingScoreDTO(
                topic_id=topic_id,
                final_score=0.0,
                strategy_name="none",
                explanation="No strategy found for context",
                computed_at=datetime.now(timezone.utc),
                context_name=context.context_name,
            )

        features = await self._feature_provider.get_features(topic_id, context)
        return strategy.score_topic(topic_id, features, context)

    async def rank_topics(
        self,
        topic_ids: list[int],
        context: RankingContextDTO,
    ) -> list[RankedTopicDTO]:
        """Rank multiple topics.

        Args:
            topic_ids: List of topic IDs to rank
            context: Ranking context

        Returns:
            List of RankedTopicDTO sorted by score
        """
        if not topic_ids:
            return []

        strategy = self.get_strategy(context.context_name)
        if not strategy:
            return []

        # Get features for all topics
        features_map = await self._feature_provider.get_features_batch(
            topic_ids, context
        )

        # Build topic_features list
        topic_features = [
            (tid, features_map[tid])
            for tid in topic_ids
            if tid in features_map
        ]

        return strategy.rank_topics(topic_features, context)

    async def rank_topics_for_feed(
        self,
        board_type: str | None = None,
        time_window_hours: int = 24,
        max_results: int = 50,
        include_unreviewed: bool = False,
    ) -> list[RankedTopicDTO]:
        """Convenience method for feed ranking.

        Args:
            board_type: Optional board type filter
            time_window_hours: Time window for recency
            max_results: Maximum results to return
            include_unreviewed: Whether to include unreviewed topics

        Returns:
            List of ranked topics for feed
        """
        context_name = f"{board_type}_feed" if board_type else "general_feed"
        context = RankingContextDTO(
            context_name=context_name,
            board_type=board_type,
            time_window_hours=time_window_hours,
            max_results=max_results,
            include_unreviewed=include_unreviewed,
        )

        # This would need topic_ids from repository
        # Placeholder for now - will be implemented with feed_service
        return []

    async def rank_topics_for_homepage(
        self,
        max_results: int = 20,
    ) -> list[RankedTopicDTO]:
        """Convenience method for homepage ranking.

        Args:
            max_results: Maximum results to return

        Returns:
            List of ranked topics for homepage
        """
        context = RankingContextDTO(
            context_name="homepage",
            time_window_hours=48,
            max_results=max_results,
            include_unreviewed=False,
            min_item_count=2,
            min_source_count=2,
        )

        # Placeholder - will be implemented with feed_service
        return []

    async def rank_topics_for_trends(
        self,
        time_window_hours: int = 72,
        max_results: int = 30,
    ) -> list[RankedTopicDTO]:
        """Convenience method for trend ranking.

        Args:
            time_window_hours: Time window for trend detection
            max_results: Maximum results to return

        Returns:
            List of ranked topics for trends
        """
        context = RankingContextDTO(
            context_name="trend",
            time_window_hours=time_window_hours,
            max_results=max_results,
            include_unreviewed=True,
        )

        # Placeholder - will be implemented with trend_ranking strategy
        return []

    def get_registered_strategies(self) -> list[str]:
        """Get list of registered strategy names.

        Returns:
            List of context names with registered strategies
        """
        return list(self._strategies.keys())

    def get_strategy_info(self) -> dict[str, Any]:
        """Get information about registered strategies.

        Returns:
            Dict with strategy information
        """
        return {
            "registered_contexts": list(self._strategies.keys()),
            "strategies": {
                name: strategy.strategy_name
                for name, strategy in self._strategies.items()
            },
            "has_default": self._default_strategy is not None,
            "default_strategy": (
                self._default_strategy.strategy_name
                if self._default_strategy
                else None
            ),
        }
