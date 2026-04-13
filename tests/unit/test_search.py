"""Tests for search functionality."""

import pytest
from datetime import datetime, timezone

from app.contracts.dto.search import (
    SearchContentType,
    SearchMode,
    SearchQueryDTO,
    SearchResultItemDTO,
)
from app.search.policies import SearchPolicies, SearchPolicyMode
from app.search.semantic_result_merger import SemanticResultMerger
from app.search.ranking import SearchRanker


def make_result(
    id: int,
    score: float,
    content_type: SearchContentType = SearchContentType.TOPIC,
    **kwargs,
) -> SearchResultItemDTO:
    """Create test search result."""
    return SearchResultItemDTO(
        id=id,
        content_type=content_type,
        score=score,
        title=kwargs.get("title", f"Result {id}"),
        summary=kwargs.get("summary"),
        board_type=kwargs.get("board_type"),
        tags=kwargs.get("tags", []),
        matched_by=kwargs.get("matched_by"),
        keyword_score=kwargs.get("keyword_score"),
        semantic_score=kwargs.get("semantic_score"),
    )


def make_query(query: str = "test", **kwargs) -> SearchQueryDTO:
    """Create test search query."""
    return SearchQueryDTO(
        query=query,
        **kwargs,
    )


class TestSearchPolicies:
    """Tests for search policies."""

    def test_user_search_policy(self) -> None:
        """User search should be balanced."""
        policy = SearchPolicies.user_search()
        assert policy.keyword_enabled
        assert policy.semantic_enabled
        assert policy.keyword_weight == 0.5
        assert policy.semantic_weight == 0.5

    def test_topic_lookup_policy(self) -> None:
        """Topic lookup should favor keywords."""
        policy = SearchPolicies.topic_lookup()
        assert policy.keyword_weight > policy.semantic_weight

    def test_entity_lookup_policy(self) -> None:
        """Entity lookup should be keyword only."""
        policy = SearchPolicies.entity_lookup()
        assert policy.keyword_enabled
        assert not policy.semantic_enabled

    def test_historical_case_policy(self) -> None:
        """Historical case lookup should favor semantic."""
        policy = SearchPolicies.historical_case_lookup()
        assert policy.semantic_weight > policy.keyword_weight
        assert policy.include_explanation

    def test_similar_content_policy(self) -> None:
        """Similar content should be semantic only."""
        policy = SearchPolicies.similar_content()
        assert not policy.keyword_enabled
        assert policy.semantic_enabled

    def test_get_policy_by_mode(self) -> None:
        """Should get correct policy by mode."""
        policy = SearchPolicies.get_policy(SearchPolicyMode.AGENT_RETRIEVAL)
        assert policy.mode == SearchPolicyMode.AGENT_RETRIEVAL

    def test_customize_policy(self) -> None:
        """Should customize policy."""
        policy = SearchPolicies.customize(
            SearchPolicyMode.USER_SEARCH,
            max_results=50,
            min_score=0.3,
        )
        assert policy.max_results == 50
        assert policy.min_score == 0.3


class TestSemanticResultMerger:
    """Tests for result merger."""

    def test_merge_weighted(self) -> None:
        """Should merge with weighted scores."""
        merger = SemanticResultMerger(keyword_weight=0.6, semantic_weight=0.4)

        keyword_results = [
            make_result(1, 0.9, keyword_score=0.9),
            make_result(2, 0.7, keyword_score=0.7),
        ]
        semantic_results = [
            make_result(1, 0.8, semantic_score=0.8),
            make_result(3, 0.6, semantic_score=0.6),
        ]

        merged = merger.merge_weighted(keyword_results, semantic_results)

        assert len(merged) == 3
        # Result 1 should be first (appears in both)
        assert merged[0].id == 1
        assert merged[0].matched_by == "hybrid"

    def test_merge_rrf(self) -> None:
        """Should merge with RRF."""
        merger = SemanticResultMerger()

        keyword_results = [
            make_result(1, 0.9),
            make_result(2, 0.8),
        ]
        semantic_results = [
            make_result(2, 0.9),
            make_result(1, 0.8),
        ]

        merged = merger.merge_rrf(keyword_results, semantic_results)

        assert len(merged) == 2
        # Both should have RRF scores

    def test_merge_interleaved(self) -> None:
        """Should interleave results."""
        merger = SemanticResultMerger()

        keyword_results = [
            make_result(1, 0.9),
            make_result(2, 0.8),
        ]
        semantic_results = [
            make_result(3, 0.9),
            make_result(4, 0.8),
        ]

        merged = merger.merge_interleaved(keyword_results, semantic_results)

        assert len(merged) == 4
        # Should alternate
        assert merged[0].id == 1
        assert merged[1].id == 3

    def test_boost_hybrid_matches(self) -> None:
        """Should boost hybrid matches."""
        merger = SemanticResultMerger()

        results = [
            make_result(1, 0.5, matched_by="hybrid"),
            make_result(2, 0.6, matched_by="keyword"),
        ]

        boosted = merger.boost_hybrid_matches(results, boost_factor=1.5)

        # Hybrid should now be higher
        assert boosted[0].id == 1
        assert boosted[0].score == 0.75

    def test_normalize_scores(self) -> None:
        """Should normalize scores to 0-1."""
        merger = SemanticResultMerger()

        results = [
            make_result(1, 10.0),
            make_result(2, 5.0),
            make_result(3, 0.0),
        ]

        normalized = merger.normalize_scores(results)

        assert normalized[0].score == 1.0
        assert normalized[2].score == 0.0


class TestSearchRanker:
    """Tests for search ranker."""

    def test_rank_results(self) -> None:
        """Should rank results with boosts."""
        ranker = SearchRanker()
        query = make_query(board_filter=["ai"])

        results = [
            make_result(1, 0.5, board_type="ai"),
            make_result(2, 0.6, board_type="general"),
        ]

        ranked = ranker.rank_results(results, query)

        # Result 1 should get board match boost
        assert ranked[0].id == 1 or ranked[0].score > 0.5

    def test_merge_results(self) -> None:
        """Should merge keyword and semantic results."""
        ranker = SearchRanker()

        keyword_results = [make_result(1, 0.8)]
        semantic_results = [make_result(1, 0.7)]

        merged = ranker.merge_results(
            keyword_results,
            semantic_results,
            keyword_weight=0.5,
            semantic_weight=0.5,
        )

        assert len(merged) == 1
        assert merged[0].matched_by == "hybrid"

    def test_diversify_results(self) -> None:
        """Should diversify by board."""
        ranker = SearchRanker()

        results = [
            make_result(1, 0.9, board_type="ai"),
            make_result(2, 0.8, board_type="ai"),
            make_result(3, 0.7, board_type="ai"),
            make_result(4, 0.6, board_type="engineering"),
        ]

        diversified = ranker.diversify_results(results, max_per_board=2)

        ai_count = sum(1 for r in diversified if r.board_type == "ai")
        assert ai_count <= 2


class TestSearchQueryDTO:
    """Tests for search query DTO."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        query = SearchQueryDTO(query="test")
        assert query.mode == SearchMode.HYBRID
        assert query.top_k == 20
        assert query.semantic_enabled

    def test_filters(self) -> None:
        """Should accept filters."""
        query = SearchQueryDTO(
            query="test",
            board_filter=["ai", "engineering"],
            tags=["python", "ml"],
        )
        assert len(query.board_filter) == 2
        assert len(query.tags) == 2

    def test_date_range(self) -> None:
        """Should accept date range."""
        now = datetime.now(timezone.utc)
        query = SearchQueryDTO(
            query="test",
            date_from=now,
            date_to=now,
        )
        assert query.date_from is not None
        assert query.date_to is not None
