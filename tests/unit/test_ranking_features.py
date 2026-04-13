"""Tests for ranking features."""

from datetime import datetime, timedelta, timezone

import pytest

from app.ranking.features import (
    compute_analyst_importance_score,
    compute_board_weight,
    compute_historian_novelty_score,
    compute_homepage_candidate_score,
    compute_recency_score,
    compute_review_pass_bonus,
    compute_source_diversity_score,
    compute_stale_penalty,
    compute_topic_size_score,
    compute_trend_signal_score,
    compute_trusted_source_score,
)


class TestRecencyScore:
    """Tests for recency score computation."""

    def test_recent_topic_high_score(self) -> None:
        """Recent topic should have high score."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=1)
        score = compute_recency_score(last_seen, time_window_hours=24, now=now)
        assert score > 0.9

    def test_old_topic_low_score(self) -> None:
        """Old topic should have low score."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=72)
        score = compute_recency_score(last_seen, time_window_hours=24, now=now)
        assert score < 0.1

    def test_at_window_boundary(self) -> None:
        """Topic at window boundary should have moderate score."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=24)
        score = compute_recency_score(last_seen, time_window_hours=24, now=now)
        assert 0.3 < score < 0.7


class TestStalePenalty:
    """Tests for stale penalty computation."""

    def test_fresh_topic_no_penalty(self) -> None:
        """Fresh topic should have no penalty."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=24)
        penalty = compute_stale_penalty(last_seen, stale_threshold_hours=72, now=now)
        assert penalty == 0.0

    def test_stale_topic_has_penalty(self) -> None:
        """Stale topic should have penalty."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=100)
        penalty = compute_stale_penalty(last_seen, stale_threshold_hours=72, now=now)
        assert penalty > 0.0

    def test_very_stale_max_penalty(self) -> None:
        """Very stale topic should have max penalty."""
        now = datetime.now(timezone.utc)
        last_seen = now - timedelta(hours=200)
        penalty = compute_stale_penalty(last_seen, stale_threshold_hours=72, now=now)
        assert penalty == 1.0


class TestSourceDiversityScore:
    """Tests for source diversity score."""

    def test_single_source_low_score(self) -> None:
        """Single source should have low score."""
        score = compute_source_diversity_score(1, max_sources=10)
        assert score < 0.5

    def test_many_sources_high_score(self) -> None:
        """Many sources should have high score."""
        score = compute_source_diversity_score(10, max_sources=10)
        assert score == 1.0

    def test_zero_sources(self) -> None:
        """Zero sources should have zero score."""
        score = compute_source_diversity_score(0, max_sources=10)
        assert score == 0.0


class TestTrustedSourceScore:
    """Tests for trusted source score."""

    def test_all_trusted(self) -> None:
        """All trusted sources should have high score."""
        score = compute_trusted_source_score(5, 5)
        assert score == 1.0

    def test_no_trusted(self) -> None:
        """No trusted sources should have zero score."""
        score = compute_trusted_source_score(0, 5)
        assert score == 0.0

    def test_half_trusted(self) -> None:
        """Half trusted should have moderate score."""
        score = compute_trusted_source_score(3, 6)
        assert 0.5 < score < 1.0


class TestTopicSizeScore:
    """Tests for topic size score."""

    def test_small_topic(self) -> None:
        """Small topic should have low score."""
        score = compute_topic_size_score(1, min_items=1, optimal_items=5)
        assert score < 0.5

    def test_optimal_topic(self) -> None:
        """Optimal size topic should have good score."""
        score = compute_topic_size_score(5, min_items=1, optimal_items=5)
        assert score >= 0.8

    def test_large_topic(self) -> None:
        """Large topic should have max score."""
        score = compute_topic_size_score(20, min_items=1, optimal_items=5, max_items=20)
        assert score == 1.0


class TestTrendSignalScore:
    """Tests for trend signal score."""

    def test_high_trend_score(self) -> None:
        """High trend score should result in high signal."""
        score = compute_trend_signal_score(0.8)
        assert score >= 0.8

    def test_with_stage_boost(self) -> None:
        """Growing stage should boost score."""
        base = compute_trend_signal_score(0.5)
        boosted = compute_trend_signal_score(0.5, stage_label="growing")
        assert boosted > base

    def test_declining_stage_penalty(self) -> None:
        """Declining stage should reduce score."""
        base = compute_trend_signal_score(0.5)
        penalized = compute_trend_signal_score(0.5, stage_label="declining")
        assert penalized < base


class TestAnalystImportanceScore:
    """Tests for analyst importance score."""

    def test_high_confidence(self) -> None:
        """High confidence should contribute to score."""
        score = compute_analyst_importance_score(
            confidence=0.9,
            trend_momentum=0.5,
            has_why_it_matters=True,
            has_system_judgement=True,
        )
        assert score > 0.7

    def test_no_data(self) -> None:
        """No data should result in low score."""
        score = compute_analyst_importance_score(
            confidence=None,
            trend_momentum=None,
            has_why_it_matters=False,
            has_system_judgement=False,
        )
        assert score == 0.0


class TestHistorianNoveltyScore:
    """Tests for historian novelty score."""

    def test_novel_topic(self) -> None:
        """Novel topic should have high score."""
        score = compute_historian_novelty_score(is_novel=True)
        assert score > 0.7

    def test_not_novel(self) -> None:
        """Not novel topic should have lower score."""
        score = compute_historian_novelty_score(is_novel=False)
        assert score < 0.5


class TestReviewPassBonus:
    """Tests for review pass bonus."""

    def test_approved(self) -> None:
        """Approved review should have full bonus."""
        bonus = compute_review_pass_bonus("approve")
        assert bonus == 1.0

    def test_rejected(self) -> None:
        """Rejected review should have no bonus."""
        bonus = compute_review_pass_bonus("reject")
        assert bonus == 0.0

    def test_revise(self) -> None:
        """Revise status should have partial bonus."""
        bonus = compute_review_pass_bonus("revise")
        assert 0.0 < bonus < 1.0


class TestHomepageCandidateScore:
    """Tests for homepage candidate score."""

    def test_good_candidate(self) -> None:
        """Good candidate should have high score."""
        score = compute_homepage_candidate_score(
            item_count=5,
            source_count=3,
            review_passed=True,
            recency_score=0.8,
            trend_score=0.7,
        )
        assert score > 0.5

    def test_not_reviewed(self) -> None:
        """Not reviewed should have zero score."""
        score = compute_homepage_candidate_score(
            item_count=5,
            source_count=3,
            review_passed=False,
            recency_score=0.8,
            trend_score=0.7,
        )
        assert score == 0.0

    def test_single_source(self) -> None:
        """Single source should have zero score."""
        score = compute_homepage_candidate_score(
            item_count=5,
            source_count=1,
            review_passed=True,
            recency_score=0.8,
            trend_score=0.7,
        )
        assert score == 0.0


class TestBoardWeight:
    """Tests for board weight computation."""

    def test_exact_match(self) -> None:
        """Exact board match should have boost."""
        weight = compute_board_weight("ai", "ai")
        assert weight > 1.0

    def test_related_boards(self) -> None:
        """Related boards should have moderate weight."""
        weight = compute_board_weight("ai", "engineering")
        assert 0.5 < weight < 1.0

    def test_no_context(self) -> None:
        """No context should have neutral weight."""
        weight = compute_board_weight("ai", None)
        assert weight == 1.0
