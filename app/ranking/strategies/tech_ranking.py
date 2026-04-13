"""Tech ranking strategy.

Prioritizes novelty, trend signals, and engineering value.
"""

from app.contracts.dto.ranking import RankingContextDTO
from app.ranking.strategies.base import BaseRankingStrategy


class TechRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for tech feed.

    Emphasizes:
    - Historian/analyst novelty assessment
    - Trend score
    - Engineering value signals
    - Source diversity
    """

    def __init__(self) -> None:
        """Initialize tech ranking strategy."""
        super().__init__("tech_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for tech ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Novelty is key for tech content
            "historian_novelty": 0.20,
            "analyst_importance": 0.15,
            # Trend signals indicate emerging tech
            "trend_signal": 0.15,
            "trend": 0.10,
            # Source diversity validates tech claims
            "source_diversity": 0.10,
            # Recency still matters but less than news
            "recency": 0.10,
            # Topic size indicates community interest
            "topic_size": 0.10,
            # Review ensures accuracy
            "review_bonus": 0.05,
            # Source authority for credibility
            "source_authority": 0.05,
        }


class DeepTechRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for deep tech content.

    More emphasis on research quality and novelty.
    """

    def __init__(self) -> None:
        """Initialize deep tech ranking strategy."""
        super().__init__("deep_tech_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for deep tech ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Novelty is paramount
            "historian_novelty": 0.25,
            # Analyst assessment of importance
            "analyst_importance": 0.20,
            # Source authority for research credibility
            "source_authority": 0.15,
            "trusted_source": 0.10,
            # Trend signals for emerging research
            "trend_signal": 0.10,
            # Review ensures quality
            "review_bonus": 0.10,
            # Recency less important for research
            "recency": 0.05,
            # Insight confidence
            "insight_confidence": 0.05,
        }


class EngineeringRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for engineering content.

    Balances practical value with novelty.
    """

    def __init__(self) -> None:
        """Initialize engineering ranking strategy."""
        super().__init__("engineering_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for engineering ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Practical value signals
            "topic_size": 0.15,
            "source_diversity": 0.15,
            # Analyst assessment
            "analyst_importance": 0.15,
            # Trend for emerging tools/practices
            "trend_signal": 0.15,
            # Recency for updates
            "recency": 0.10,
            # Novelty for new approaches
            "historian_novelty": 0.10,
            # Review for accuracy
            "review_bonus": 0.10,
            # Topic heat for community interest
            "topic_heat": 0.10,
        }
