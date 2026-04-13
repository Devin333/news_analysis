"""News ranking strategy.

Prioritizes timeliness, source credibility, and industry impact.
"""

from app.contracts.dto.ranking import RankingContextDTO
from app.ranking.strategies.base import BaseRankingStrategy


class NewsRankingStrategy(BaseRankingStrategy):
    """Ranking strategy for news feed.

    Emphasizes:
    - Timeliness (recency)
    - Source credibility
    - Industry impact
    - Review status
    """

    def __init__(self) -> None:
        """Initialize news ranking strategy."""
        super().__init__("news_ranking")

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights for news ranking.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        return {
            # High weight on recency - news must be fresh
            "recency": 0.30,
            # Source credibility is important
            "source_authority": 0.15,
            "trusted_source": 0.15,
            # Topic heat indicates breaking news
            "topic_heat": 0.10,
            # Multiple sources validate the story
            "source_diversity": 0.10,
            # Review ensures quality
            "review_bonus": 0.10,
            # Analyst insight adds value
            "analyst_importance": 0.05,
            # Trend signal for emerging stories
            "trend_signal": 0.05,
        }


class BoardNewsRankingStrategy(BaseRankingStrategy):
    """News ranking strategy for specific board.

    Adjusts weights based on board type.
    """

    def __init__(self, board_type: str) -> None:
        """Initialize board-specific news ranking.

        Args:
            board_type: Target board type
        """
        super().__init__(f"news_ranking_{board_type}")
        self._board_type = board_type

    def get_weights(self, context: RankingContextDTO) -> dict[str, float]:
        """Get feature weights adjusted for board.

        Args:
            context: Ranking context

        Returns:
            Dict mapping feature names to weights
        """
        base_weights = {
            "recency": 0.25,
            "source_authority": 0.15,
            "trusted_source": 0.15,
            "topic_heat": 0.10,
            "source_diversity": 0.10,
            "review_bonus": 0.10,
            "analyst_importance": 0.10,
            "trend_signal": 0.05,
        }

        # Adjust for AI board - more weight on analyst insight
        if self._board_type == "ai":
            base_weights["analyst_importance"] = 0.15
            base_weights["trend_signal"] = 0.10
            base_weights["recency"] = 0.20

        # Adjust for research board - more weight on source authority
        elif self._board_type == "research":
            base_weights["source_authority"] = 0.20
            base_weights["trusted_source"] = 0.20
            base_weights["recency"] = 0.15

        # Adjust for engineering board - balance
        elif self._board_type == "engineering":
            base_weights["topic_size"] = 0.10
            base_weights["source_diversity"] = 0.15

        return base_weights
