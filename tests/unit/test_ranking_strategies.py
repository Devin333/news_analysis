"""Tests for ranking strategies."""

import pytest

from app.contracts.dto.ranking import RankingContextDTO, RankingFeatureDTO
from app.ranking.strategies.base import BaseRankingStrategy
from app.ranking.strategies.homepage_ranking import HomepageRankingStrategy
from app.ranking.strategies.news_ranking import NewsRankingStrategy
from app.ranking.strategies.tech_ranking import TechRankingStrategy
from app.ranking.strategies.trend_ranking import TrendRankingStrategy


def make_features(
    topic_id: int,
    recency: float = 0.5,
    trend: float = 0.5,
    review_passed: bool = True,
    **kwargs,
) -> RankingFeatureDTO:
    """Create test features."""
    return RankingFeatureDTO(
        topic_id=topic_id,
        recency_score=recency,
        trend_score=trend,
        trend_signal_score=kwargs.get("trend_signal", trend),
        source_diversity_score=kwargs.get("source_diversity", 0.5),
        source_authority_score=kwargs.get("source_authority", 0.5),
        trusted_source_score=kwargs.get("trusted_source", 0.5),
        topic_heat_score=kwargs.get("topic_heat", 0.5),
        topic_size_score=kwargs.get("topic_size", 0.5),
        analyst_importance_score=kwargs.get("analyst_importance", 0.5),
        historian_novelty_score=kwargs.get("historian_novelty", 0.5),
        review_passed=review_passed,
        review_pass_bonus=1.0 if review_passed else 0.0,
        homepage_candidate_score=kwargs.get("homepage_candidate", 0.5),
        item_count=kwargs.get("item_count", 5),
        source_count=kwargs.get("source_count", 3),
        board_weight=kwargs.get("board_weight", 1.0),
    )


def make_context(name: str = "test", **kwargs) -> RankingContextDTO:
    """Create test context."""
    return RankingContextDTO(
        context_name=name,
        time_window_hours=kwargs.get("time_window_hours", 24),
        max_results=kwargs.get("max_results", 20),
        include_unreviewed=kwargs.get("include_unreviewed", False),
    )


class TestNewsRankingStrategy:
    """Tests for news ranking strategy."""

    def test_strategy_name(self) -> None:
        """Strategy should have correct name."""
        strategy = NewsRankingStrategy()
        assert strategy.strategy_name == "news_ranking"

    def test_recency_weight_high(self) -> None:
        """Recency should have high weight in news."""
        strategy = NewsRankingStrategy()
        weights = strategy.get_weights(make_context())
        assert weights["recency"] >= 0.25

    def test_score_topic(self) -> None:
        """Should score topic correctly."""
        strategy = NewsRankingStrategy()
        features = make_features(1, recency=0.9, trend=0.5)
        context = make_context()
        
        score = strategy.score_topic(1, features, context)
        
        assert score.topic_id == 1
        assert score.final_score > 0
        assert score.strategy_name == "news_ranking"

    def test_recent_topic_ranks_higher(self) -> None:
        """Recent topic should rank higher than old."""
        strategy = NewsRankingStrategy()
        context = make_context()
        
        recent = make_features(1, recency=0.9)
        old = make_features(2, recency=0.1)
        
        recent_score = strategy.score_topic(1, recent, context)
        old_score = strategy.score_topic(2, old, context)
        
        assert recent_score.final_score > old_score.final_score


class TestTechRankingStrategy:
    """Tests for tech ranking strategy."""

    def test_strategy_name(self) -> None:
        """Strategy should have correct name."""
        strategy = TechRankingStrategy()
        assert strategy.strategy_name == "tech_ranking"

    def test_novelty_weight_high(self) -> None:
        """Novelty should have high weight in tech."""
        strategy = TechRankingStrategy()
        weights = strategy.get_weights(make_context())
        assert weights["historian_novelty"] >= 0.15

    def test_novel_topic_ranks_higher(self) -> None:
        """Novel topic should rank higher."""
        strategy = TechRankingStrategy()
        context = make_context()
        
        novel = make_features(1, historian_novelty=0.9)
        common = make_features(2, historian_novelty=0.1)
        
        novel_score = strategy.score_topic(1, novel, context)
        common_score = strategy.score_topic(2, common, context)
        
        assert novel_score.final_score > common_score.final_score


class TestHomepageRankingStrategy:
    """Tests for homepage ranking strategy."""

    def test_strategy_name(self) -> None:
        """Strategy should have correct name."""
        strategy = HomepageRankingStrategy()
        assert strategy.strategy_name == "homepage_ranking"

    def test_review_required(self) -> None:
        """Review should be important for homepage."""
        strategy = HomepageRankingStrategy()
        weights = strategy.get_weights(make_context())
        assert weights["review_bonus"] >= 0.15

    def test_reviewed_ranks_higher(self) -> None:
        """Reviewed topic should rank higher."""
        strategy = HomepageRankingStrategy()
        context = make_context()
        
        reviewed = make_features(1, review_passed=True)
        unreviewed = make_features(2, review_passed=False)
        
        reviewed_score = strategy.score_topic(1, reviewed, context)
        unreviewed_score = strategy.score_topic(2, unreviewed, context)
        
        assert reviewed_score.final_score > unreviewed_score.final_score


class TestTrendRankingStrategy:
    """Tests for trend ranking strategy."""

    def test_strategy_name(self) -> None:
        """Strategy should have correct name."""
        strategy = TrendRankingStrategy()
        assert strategy.strategy_name == "trend_ranking"

    def test_trend_weight_high(self) -> None:
        """Trend signal should have high weight."""
        strategy = TrendRankingStrategy()
        weights = strategy.get_weights(make_context())
        assert weights["trend_signal"] >= 0.25

    def test_trending_topic_ranks_higher(self) -> None:
        """Trending topic should rank higher."""
        strategy = TrendRankingStrategy()
        context = make_context()
        
        trending = make_features(1, trend=0.9, trend_signal=0.9)
        stable = make_features(2, trend=0.1, trend_signal=0.1)
        
        trending_score = strategy.score_topic(1, trending, context)
        stable_score = strategy.score_topic(2, stable, context)
        
        assert trending_score.final_score > stable_score.final_score


class TestRankTopics:
    """Tests for ranking multiple topics."""

    def test_rank_topics_sorted(self) -> None:
        """Topics should be sorted by score."""
        strategy = NewsRankingStrategy()
        context = make_context(max_results=10)
        
        topic_features = [
            (1, make_features(1, recency=0.3)),
            (2, make_features(2, recency=0.9)),
            (3, make_features(3, recency=0.6)),
        ]
        
        ranked = strategy.rank_topics(topic_features, context)
        
        assert len(ranked) == 3
        assert ranked[0].topic_id == 2  # Highest recency
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3

    def test_rank_topics_respects_max_results(self) -> None:
        """Should respect max_results limit."""
        strategy = NewsRankingStrategy()
        context = make_context(max_results=2)
        
        topic_features = [
            (1, make_features(1)),
            (2, make_features(2)),
            (3, make_features(3)),
        ]
        
        ranked = strategy.rank_topics(topic_features, context)
        
        assert len(ranked) == 2

    def test_rank_topics_empty_list(self) -> None:
        """Should handle empty list."""
        strategy = NewsRankingStrategy()
        context = make_context()
        
        ranked = strategy.rank_topics([], context)
        
        assert ranked == []
