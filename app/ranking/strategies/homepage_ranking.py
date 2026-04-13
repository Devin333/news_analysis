"""Homepage ranking strategy.

Prioritizes overall importance, readability, and board balance.
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


class HomepageRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for homepage.

    Emphasizes:
    - Overall importance
    - Readability (review passed)
    - Board balance
    - Review status
    - Deduplication
    """

    def __init__(self) -> None:
        """Initialize homepage ranking strategy."""
        super().__init__("homepage_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for homepage ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Homepage candidate score is pre-computed
            "homepage_candidate": 0.25,
            # Review is mandatory for homepage
            "review_bonus": 0.20,
            # Analyst importance for value
            "analyst_importance": 0.15,
            # Trend for interesting content
            "trend_signal": 0.10,
            # Recency for freshness
            "recency": 0.10,
            # Source diversity for credibility
            "source_diversity": 0.10,
            # Topic heat for engagement
            "topic_heat": 0.10,
        }

    def rank_topics(
        self,
        topic_features: list[tuple[int, RankingFeatureDTO]],
        context: RankingContextDTO,
    ) -> list[RankedTopicDTO]:
        """Rank topics with board balancing.

        Args:
            topic_features: List of (topic_id, features) tuples
            context: Ranking context

        Returns:
            List of RankedTopicDTO with board balance
        """
        # First, get base ranking
        base_ranking = super().rank_topics(topic_features, context)

        # Apply board balancing
        return self._apply_board_balance(base_ranking, context)

    def _apply_board_balance(
        self,
        ranked: list[RankedTopicDTO],
        context: RankingContextDTO,
        max_per_board: int = 5,
    ) -> list[RankedTopicDTO]:
        """Apply board balancing to ranking.

        Ensures no single board dominates the homepage.

        Args:
            ranked: Base ranked list
            context: Ranking context
            max_per_board: Maximum topics per board

        Returns:
            Balanced ranked list
        """
        board_counts: dict[str, int] = {}
        balanced = []

        for topic in ranked:
            board = topic.board_type or "general"
            current_count = board_counts.get(board, 0)

            if current_count < max_per_board:
                balanced.append(topic)
                board_counts[board] = current_count + 1

            if len(balanced) >= context.max_results:
                break

        # Re-rank
        for i, topic in enumerate(balanced, start=1):
            topic.rank = i

        return balanced


class DiversifiedHomepageStrategy(BaseRankingStrategy):
    """Homepage strategy with diversity optimization.

    Ensures content variety across multiple dimensions.
    """

    def __init__(self) -> None:
        """Initialize diversified homepage strategy."""
        super().__init__("diversified_homepage")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            "homepage_candidate": 0.20,
            "review_bonus": 0.20,
            "analyst_importance": 0.15,
            "trend_signal": 0.15,
            "recency": 0.10,
            "source_diversity": 0.10,
            "historian_novelty": 0.10,
        }

    def rank_topics(
        self,
        topic_features: list[tuple[int, RankingFeatureDTO]],
        context: RankingContextDTO,
    ) -> list[RankedTopicDTO]:
        """Rank with diversity optimization.

        Uses MMR-like approach for diversity.

        Args:
            topic_features: List of (topic_id, features) tuples
            context: Ranking context

        Returns:
            Diversified ranked list
        """
        if not topic_features:
            return []

        # Score all topics
        scored = []
        for topic_id, features in topic_features:
            score_dto = self.score_topic(topic_id, features, context)
            scored.append((topic_id, features, score_dto))

        # Sort by score
        scored.sort(key=lambda x: x[2].final_score, reverse=True)

        # Apply diversity selection
        selected = []
        remaining = list(scored)
        lambda_param = 0.7  # Balance between relevance and diversity

        while remaining and len(selected) < context.max_results:
            if not selected:
                # First item is highest scored
                selected.append(remaining.pop(0))
            else:
                # Find item with best MMR score
                best_idx = 0
                best_mmr = float("-inf")

                for i, (tid, features, score_dto) in enumerate(remaining):
                    relevance = score_dto.final_score
                    diversity = self._compute_diversity(features, selected)
                    mmr = lambda_param * relevance + (1 - lambda_param) * diversity

                    if mmr > best_mmr:
                        best_mmr = mmr
                        best_idx = i

                selected.append(remaining.pop(best_idx))

        # Build result
        result = []
        for rank, (topic_id, features, score_dto) in enumerate(selected, start=1):
            result.append(
                RankedTopicDTO(
                    topic_id=topic_id,
                    rank=rank,
                    score=score_dto.final_score,
                    title="",
                    board_type="",
                    strategy_name=self._name,
                    features=features,
                    score_breakdown=score_dto.component_scores,
                    item_count=features.item_count,
                )
            )

        return result

    def _compute_diversity(
        self,
        candidate: RankingFeatureDTO,
        selected: list[tuple[int, RankingFeatureDTO, RankingScoreDTO]],
    ) -> float:
        """Compute diversity score for candidate.

        Args:
            candidate: Candidate features
            selected: Already selected items

        Returns:
            Diversity score (higher = more diverse)
        """
        if not selected:
            return 1.0

        # Simple diversity based on feature distance
        min_distance = float("inf")

        for _, sel_features, _ in selected:
            distance = self._feature_distance(candidate, sel_features)
            min_distance = min(min_distance, distance)

        return min_distance

    def _feature_distance(
        self,
        f1: RankingFeatureDTO,
        f2: RankingFeatureDTO,
    ) -> float:
        """Compute distance between two feature vectors.

        Args:
            f1: First feature set
            f2: Second feature set

        Returns:
            Distance value
        """
        # Simple Euclidean-like distance on key features
        diff_recency = abs(f1.recency_score - f2.recency_score)
        diff_trend = abs(f1.trend_signal_score - f2.trend_signal_score)
        diff_heat = abs(f1.topic_heat_score - f2.topic_heat_score)

        return (diff_recency + diff_trend + diff_heat) / 3
