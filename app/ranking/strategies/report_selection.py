"""Report selection strategy.

Selects topics for daily/weekly reports.
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


class ReportSelectionStrategy(BaseRankingStrategy):
    """Strategy for selecting topics for reports.

    Selects:
    - Top topics
    - Rising trends
    - Editor picks
    """

    def __init__(self) -> None:
        """Initialize report selection strategy."""
        super().__init__("report_selection")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for report selection.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Review is mandatory for reports
            "review_bonus": 0.25,
            # Analyst importance for value
            "analyst_importance": 0.20,
            # Homepage candidate score
            "homepage_candidate": 0.15,
            # Trend signals for interesting content
            "trend_signal": 0.15,
            # Source diversity for credibility
            "source_diversity": 0.10,
            # Topic heat for engagement
            "topic_heat": 0.10,
            # Recency
            "recency": 0.05,
        }

    def select_for_report(
        self,
        topic_features: list[tuple[int, RankingFeatureDTO]],
        context: RankingContextDTO,
        sections: dict[str, int] | None = None,
    ) -> dict[str, list[RankedTopicDTO]]:
        """Select topics for different report sections.

        Args:
            topic_features: List of (topic_id, features) tuples
            context: Ranking context
            sections: Dict mapping section name to count

        Returns:
            Dict mapping section name to ranked topics
        """
        if sections is None:
            sections = {
                "top_stories": 5,
                "rising_trends": 3,
                "deep_dives": 2,
            }

        # Get base ranking
        all_ranked = self.rank_topics(topic_features, context)

        # Filter reviewed only
        reviewed = [t for t in all_ranked if t.features and t.features.review_passed]

        result: dict[str, list[RankedTopicDTO]] = {}
        used_ids: set[int] = set()

        # Top stories - highest overall score
        result["top_stories"] = self._select_section(
            reviewed, sections.get("top_stories", 5), used_ids
        )

        # Rising trends - high trend signal
        trend_sorted = sorted(
            [t for t in reviewed if t.topic_id not in used_ids],
            key=lambda t: t.features.trend_signal_score if t.features else 0,
            reverse=True,
        )
        result["rising_trends"] = self._select_section(
            trend_sorted, sections.get("rising_trends", 3), used_ids
        )

        # Deep dives - high analyst importance
        deep_sorted = sorted(
            [t for t in reviewed if t.topic_id not in used_ids],
            key=lambda t: t.features.analyst_importance_score if t.features else 0,
            reverse=True,
        )
        result["deep_dives"] = self._select_section(
            deep_sorted, sections.get("deep_dives", 2), used_ids
        )

        return result

    def _select_section(
        self,
        candidates: list[RankedTopicDTO],
        count: int,
        used_ids: set[int],
    ) -> list[RankedTopicDTO]:
        """Select topics for a section.

        Args:
            candidates: Candidate topics
            count: Number to select
            used_ids: Already used topic IDs

        Returns:
            Selected topics
        """
        selected = []
        for topic in candidates:
            if topic.topic_id not in used_ids:
                selected.append(topic)
                used_ids.add(topic.topic_id)
                if len(selected) >= count:
                    break

        # Re-rank within section
        for i, topic in enumerate(selected, start=1):
            topic.rank = i

        return selected


class DailyReportStrategy(ReportSelectionStrategy):
    """Strategy for daily report selection.

    More emphasis on recency.
    """

    def __init__(self) -> None:
        """Initialize daily report strategy."""
        BaseRankingStrategy.__init__(self, "daily_report")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for daily report.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            "review_bonus": 0.20,
            "recency": 0.20,  # Higher for daily
            "analyst_importance": 0.15,
            "trend_signal": 0.15,
            "topic_heat": 0.15,
            "source_diversity": 0.10,
            "homepage_candidate": 0.05,
        }


class WeeklyReportStrategy(ReportSelectionStrategy):
    """Strategy for weekly report selection.

    More emphasis on importance and trends.
    """

    def __init__(self) -> None:
        """Initialize weekly report strategy."""
        BaseRankingStrategy.__init__(self, "weekly_report")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for weekly report.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            "review_bonus": 0.20,
            "analyst_importance": 0.20,  # Higher for weekly
            "trend_signal": 0.20,  # Higher for weekly
            "homepage_candidate": 0.15,
            "source_diversity": 0.10,
            "topic_heat": 0.10,
            "recency": 0.05,  # Lower for weekly
        }


class EditorPickStrategy(BaseRankingStrategy):
    """Strategy for editor's picks.

    Balances quality, novelty, and reader interest.
    """

    def __init__(self) -> None:
        """Initialize editor pick strategy."""
        super().__init__("editor_pick")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for editor picks.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # Quality is paramount
            "review_bonus": 0.25,
            # Novelty for interesting content
            "historian_novelty": 0.20,
            # Analyst assessment
            "analyst_importance": 0.20,
            # Trend for relevance
            "trend_signal": 0.15,
            # Source credibility
            "source_authority": 0.10,
            # Insight confidence
            "insight_confidence": 0.10,
        }
