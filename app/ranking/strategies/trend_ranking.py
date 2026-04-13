"""Trend ranking strategy.

Prioritizes trend stage, signal strength, and cross-source resonance.
"""

from datetime import datetime, timezone
from typing import Any

from app.contracts.dto.ranking import (
    RankedTopicDTO,
    RankingContextDTO,
    RankingFeatureDTO,
    RankingScoreDTO,
)
from app.ranking.strategies.base import BaseRankingStrategy


class TrendRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for trend page.

    Emphasizes:
    - Trend stage (emerging, growing, peak)
    - Signal strength
    - Repeated appearance
    - Cross-source resonance
    """

    def __init__(self) -> None:
        """Initialize trend ranking strategy."""
        super().__init__("trend_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for trend ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Trend signals are primary
            "trend_signal": 0.30,
            "trend": 0.20,
            # Topic heat indicates momentum
            "topic_heat": 0.15,
            # Source diversity validates trend
            "source_diversity": 0.10,
            # Analyst importance for value
            "analyst_importance": 0.10,
            # Recency for emerging trends
            "recency": 0.10,
            # Topic size for validation
            "topic_size": 0.05,
        }

    def score_topic(
        self,
        topic_id: int,
        features: RankingFeatureDTO,
        context: RankingContextDTO,
    ) -> RankingScoreDTO:
        """Score topic with trend-specific adjustments.

        Args:
            topic_id: The topic to score
            features: Pre-computed features
            context: Ranking context

        Returns:
            RankingScoreDTO with trend-adjusted score
        """
        # Get base score
        base_score = super().score_topic(topic_id, features, context)

        # Apply trend stage boost
        stage_boost = self._get_stage_boost(features)
        adjusted_score = base_score.final_score * (1 + stage_boost)

        # Update component scores
        component_scores = dict(base_score.component_scores)
        component_scores["stage_boost"] = stage_boost

        return RankingScoreDTO(
            topic_id=topic_id,
            final_score=adjusted_score,
            strategy_name=self._name,
            component_scores=component_scores,
            explanation=f"Trend score with stage boost: {stage_boost:.2f}",
            top_factors=base_score.top_factors + ["stage_boost"],
            computed_at=datetime.now(timezone.utc),
            context_name=context.context_name,
        )

    def _get_stage_boost(self, features: RankingFeatureDTO) -> float:
        """Get boost based on trend stage.

        Args:
            features: Topic features

        Returns:
            Boost multiplier
        """
        # Infer stage from trend signals
        trend_score = features.trend_signal_score

        if trend_score >= 0.8:
            return 0.3  # Peak - high boost
        elif trend_score >= 0.6:
            return 0.4  # Growing - highest boost
        elif trend_score >= 0.4:
            return 0.3  # Emerging - good boost
        elif trend_score >= 0.2:
            return 0.1  # Early - small boost
        else:
            return 0.0  # No trend signal


class EmergingTrendStrategy(BaseRankingStrategy):
    """Strategy focused on emerging trends.

    Prioritizes early-stage trends with growth potential.
    """

    def __init__(self) -> None:
        """Initialize emerging trend strategy."""
        super().__init__("emerging_trend")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for emerging trends.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Novelty is key for emerging
            "historian_novelty": 0.25,
            # Trend signals
            "trend_signal": 0.20,
            # Recency for freshness
            "recency": 0.20,
            # Analyst assessment
            "analyst_importance": 0.15,
            # Source diversity for validation
            "source_diversity": 0.10,
            # Topic heat for momentum
            "topic_heat": 0.10,
        }


class HotTrendStrategy(BaseRankingStrategy):
    """Strategy focused on hot/peak trends.

    Prioritizes high-momentum trends at peak.
    """

    def __init__(self) -> None:
        """Initialize hot trend strategy."""
        super().__init__("hot_trend")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for hot trends.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Topic heat is primary
            "topic_heat": 0.25,
            # Trend signals
            "trend_signal": 0.20,
            "trend": 0.15,
            # Source diversity for validation
            "source_diversity": 0.15,
            # Topic size for scale
            "topic_size": 0.10,
            # Recency
            "recency": 0.10,
            # Review for quality
            "review_bonus": 0.05,
        }
