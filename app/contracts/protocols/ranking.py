"""Ranking protocols for strategy and feature providers."""

from typing import Protocol, runtime_checkable

from app.contracts.dto.ranking import (
    RankedTopicDTO,
    RankingContextDTO,
    RankingFeatureDTO,
    RankingScoreDTO,
)


@runtime_checkable
class RankingStrategyProtocol(Protocol):
    """Protocol for ranking strategies.

    Different strategies can be implemented for different contexts:
    - News feed ranking
    - Tech feed ranking
    - Homepage ranking
    - Trend ranking
    """

    @property
    def strategy_name(self) -> str:
        """Return the name of this strategy."""
        ...

    def score_topic(
        self,
        topic_id: int,
        features: RankingFeatureDTO,
        context: RankingContextDTO,
    ) -> RankingScoreDTO:
        """Score a single topic based on its features.

        Args:
            topic_id: The topic to score
            features: Pre-computed features for the topic
            context: Ranking context with weights and filters

        Returns:
            RankingScoreDTO with final score and breakdown
        """
        ...

    def rank_topics(
        self,
        topic_features: list[tuple[int, RankingFeatureDTO]],
        context: RankingContextDTO,
    ) -> list[RankedTopicDTO]:
        """Rank multiple topics.

        Args:
            topic_features: List of (topic_id, features) tuples
            context: Ranking context

        Returns:
            List of RankedTopicDTO sorted by score descending
        """
        ...


@runtime_checkable
class RankingFeatureProviderProtocol(Protocol):
    """Protocol for providing ranking features.

    Responsible for extracting and computing features
    from various data sources.
    """

    async def get_features(
        self,
        topic_id: int,
        context: RankingContextDTO,
    ) -> RankingFeatureDTO:
        """Get ranking features for a single topic.

        Args:
            topic_id: The topic to get features for
            context: Ranking context

        Returns:
            RankingFeatureDTO with all computed features
        """
        ...

    async def get_features_batch(
        self,
        topic_ids: list[int],
        context: RankingContextDTO,
    ) -> dict[int, RankingFeatureDTO]:
        """Get ranking features for multiple topics.

        Args:
            topic_ids: List of topic IDs
            context: Ranking context

        Returns:
            Dict mapping topic_id to RankingFeatureDTO
        """
        ...
