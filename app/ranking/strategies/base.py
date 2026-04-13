"""Base ranking strategy implementation."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.contracts.dto.ranking import (
    RankedTopicDTO,
    RankingContextDTO,
    RankingFeatureDTO,
    RankingScoreDTO,
)
from app.contracts.protocols.ranking import RankingStrategyProtocol


class BaseRankingStrategy(ABC, RankingStrategyProtocol):
    """Base class for ranking strategies.

    Provides common functionality for all ranking strategies.
    """

    def __init__(self, name: str) -> None:
        """Initialize strategy.

        Args:
            name: Strategy name
        """
        self._name = name

    @property
    def strategy_name(self) -> str:
        """Return the name of this strategy."""
        return self._name

    @abstractmethod
    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for this strategy.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
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
        weights = self.get_weights(context)

        # Apply custom weights from context
        if context.custom_weights:
            weights.update(context.custom_weights)

        # Compute component scores
        component_scores = self._compute_component_scores(features, weights)

        # Compute final score
        final_score = sum(component_scores.values())

        # Apply penalties
        final_score = self._apply_penalties(final_score, features, context)

        # Apply board weight
        final_score *= features.board_weight

        # Get top factors
        top_factors = self._get_top_factors(component_scores)

        return RankingScoreDTO(
            topic_id=topic_id,
            final_score=final_score,
            strategy_name=self._name,
            component_scores=component_scores,
            explanation=self._generate_explanation(component_scores, top_factors),
            top_factors=top_factors,
            computed_at=datetime.now(timezone.utc),
            context_name=context.context_name,
        )

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
        # Score all topics
        scored = []
        for topic_id, features in topic_features:
            score_dto = self.score_topic(topic_id, features, context)
            scored.append((topic_id, features, score_dto))

        # Sort by score descending
        scored.sort(key=lambda x: x[2].final_score, reverse=True)

        # Apply max_results limit
        if context.max_results > 0:
            scored = scored[:context.max_results]

        # Build ranked list
        result = []
        for rank, (topic_id, features, score_dto) in enumerate(scored, start=1):
            result.append(
                RankedTopicDTO(
                    topic_id=topic_id,
                    rank=rank,
                    score=score_dto.final_score,
                    title="",  # Will be filled by caller
                    board_type="",  # Will be filled by caller
                    strategy_name=self._name,
                    features=features,
                    score_breakdown=score_dto.component_scores,
                    item_count=features.item_count,
                )
            )

        return result

    def _compute_component_scores(
        self,
        features: RankingFeatureDTO,
        weights: dict[str, float],
    ) -> dict[str, float]:
        """Compute weighted component scores.

        Args:
            features: Feature values
            weights: Feature weights

        Returns:
            Dict mapping component names to weighted scores
        """
        scores = {}

        feature_map = {
            "recency": features.recency_score,
            "source_authority": features.source_authority_score,
            "source_diversity": features.source_diversity_score,
            "trusted_source": features.trusted_source_score,
            "topic_heat": features.topic_heat_score,
            "topic_size": features.topic_size_score,
            "trend": features.trend_score,
            "trend_signal": features.trend_signal_score,
            "insight_confidence": features.insight_confidence,
            "analyst_importance": features.analyst_importance_score,
            "historian_novelty": features.historian_novelty_score,
            "review_bonus": features.review_pass_bonus,
            "homepage_candidate": features.homepage_candidate_score,
        }

        for name, value in feature_map.items():
            if name in weights:
                scores[name] = value * weights[name]

        return scores

    def _apply_penalties(
        self,
        score: float,
        features: RankingFeatureDTO,
        context: RankingContextDTO,
    ) -> float:
        """Apply penalties to score.

        Args:
            score: Current score
            features: Feature values
            context: Ranking context

        Returns:
            Adjusted score
        """
        # Stale penalty
        score -= features.stale_penalty * 0.3

        # Minimum requirements penalty
        if features.item_count < context.min_item_count:
            score *= 0.5
        if features.source_count < context.min_source_count:
            score *= 0.7

        # Review requirement
        if not context.include_unreviewed and not features.review_passed:
            score *= 0.3

        return max(0.0, score)

    def _get_top_factors(
        self,
        component_scores: dict[str, float],
        top_n: int = 3,
    ) -> list[str]:
        """Get top contributing factors.

        Args:
            component_scores: Component scores
            top_n: Number of top factors

        Returns:
            List of top factor names
        """
        sorted_scores = sorted(
            component_scores.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        return [name for name, _ in sorted_scores[:top_n]]

    def _generate_explanation(
        self,
        component_scores: dict[str, float],
        top_factors: list[str],
    ) -> str:
        """Generate human-readable explanation.

        Args:
            component_scores: Component scores
            top_factors: Top contributing factors

        Returns:
            Explanation string
        """
        if not top_factors:
            return "No significant factors"

        parts = []
        for factor in top_factors:
            score = component_scores.get(factor, 0)
            if score > 0:
                parts.append(f"{factor}(+{score:.2f})")
            elif score < 0:
                parts.append(f"{factor}({score:.2f})")

        return f"Top factors: {', '.join(parts)}"
