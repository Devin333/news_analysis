"""Unit tests for similarity and merge scoring."""

from datetime import datetime, timedelta, timezone

import pytest

from app.processing.clustering.similarity import (
    SimilarityCalculator,
    board_type_match,
    content_type_match,
    entity_overlap_score,
    source_overlap_score,
    summary_similarity,
    tag_similarity,
    time_overlap_score,
    title_similarity,
)


class TestTitleSimilarity:
    """Tests for title_similarity function."""

    def test_identical_titles(self) -> None:
        """Identical titles should have similarity 1.0."""
        assert title_similarity("Hello World", "Hello World") == 1.0

    def test_similar_titles(self) -> None:
        """Similar titles should have high similarity."""
        score = title_similarity(
            "OpenAI releases GPT-5",
            "OpenAI announces GPT-5 launch",
        )
        assert score > 0.3

    def test_different_titles(self) -> None:
        """Different titles should have low similarity."""
        score = title_similarity(
            "Apple announces iPhone",
            "Google releases Android",
        )
        assert score < 0.3


class TestSummarySimilarity:
    """Tests for summary_similarity function."""

    def test_identical_summaries(self) -> None:
        """Identical summaries should have similarity 1.0."""
        text = "This is a test summary about machine learning"
        assert summary_similarity(text, text) == 1.0

    def test_similar_summaries(self) -> None:
        """Similar summaries should have moderate similarity."""
        s1 = "Machine learning is transforming artificial intelligence"
        s2 = "Artificial intelligence uses machine learning techniques"
        score = summary_similarity(s1, s2)
        assert 0.3 < score < 0.8

    def test_none_summaries(self) -> None:
        """None summaries should return 0.0."""
        assert summary_similarity(None, "test") == 0.0
        assert summary_similarity("test", None) == 0.0


class TestTimeOverlapScore:
    """Tests for time_overlap_score function."""

    def test_same_time(self) -> None:
        """Same time should have score 1.0."""
        now = datetime.now(timezone.utc)
        assert time_overlap_score(now, now) == 1.0

    def test_recent_times(self) -> None:
        """Recent times should have high score."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        score = time_overlap_score(now, one_hour_ago)
        assert score > 0.9

    def test_old_times(self) -> None:
        """Old times should have low score."""
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)
        score = time_overlap_score(now, one_week_ago)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_none_times(self) -> None:
        """None times should return neutral score."""
        now = datetime.now(timezone.utc)
        assert time_overlap_score(None, now) == 0.5
        assert time_overlap_score(now, None) == 0.5


class TestTagSimilarity:
    """Tests for tag_similarity function."""

    def test_identical_tags(self) -> None:
        """Identical tags should have similarity 1.0."""
        tags = ["ai", "ml", "python"]
        assert tag_similarity(tags, tags) == 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap should have moderate similarity."""
        tags1 = ["ai", "ml", "python"]
        tags2 = ["ai", "ml", "java"]
        score = tag_similarity(tags1, tags2)
        assert score == 0.5  # 2/4 overlap

    def test_no_overlap(self) -> None:
        """No overlap should have similarity 0.0."""
        tags1 = ["ai", "ml"]
        tags2 = ["web", "frontend"]
        assert tag_similarity(tags1, tags2) == 0.0


class TestSourceOverlapScore:
    """Tests for source_overlap_score function."""

    def test_same_sources(self) -> None:
        """Same sources should have score 1.0."""
        sources = [1, 2, 3]
        assert source_overlap_score(sources, sources) == 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap should have moderate score."""
        sources1 = [1, 2, 3]
        sources2 = [2, 3, 4]
        score = source_overlap_score(sources1, sources2)
        assert score == 0.5  # 2/4 overlap

    def test_no_overlap(self) -> None:
        """No overlap should have score 0.0."""
        sources1 = [1, 2]
        sources2 = [3, 4]
        assert source_overlap_score(sources1, sources2) == 0.0

    def test_empty_sources(self) -> None:
        """Empty sources should return 0.0."""
        assert source_overlap_score([], [1, 2]) == 0.0
        assert source_overlap_score([1, 2], []) == 0.0


class TestEntityOverlapScore:
    """Tests for entity_overlap_score function."""

    def test_same_entities(self) -> None:
        """Same entities should have score 1.0."""
        entities = ["OpenAI", "GPT-5"]
        assert entity_overlap_score(entities, entities) == 1.0

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        entities1 = ["OpenAI", "GPT"]
        entities2 = ["openai", "gpt"]
        assert entity_overlap_score(entities1, entities2) == 1.0

    def test_empty_entities(self) -> None:
        """Empty entities should return 0.0."""
        assert entity_overlap_score([], ["OpenAI"]) == 0.0


class TestContentTypeMatch:
    """Tests for content_type_match function."""

    def test_matching_types(self) -> None:
        """Matching types should return 1.0."""
        assert content_type_match("article", "article") == 1.0

    def test_different_types(self) -> None:
        """Different types should return 0.0."""
        assert content_type_match("article", "video") == 0.0

    def test_none_types(self) -> None:
        """None types should return neutral 0.5."""
        assert content_type_match(None, "article") == 0.5
        assert content_type_match("article", None) == 0.5


class TestBoardTypeMatch:
    """Tests for board_type_match function."""

    def test_matching_boards(self) -> None:
        """Matching boards should return 1.0."""
        assert board_type_match("ai", "ai") == 1.0

    def test_different_boards(self) -> None:
        """Different boards should return 0.0."""
        assert board_type_match("ai", "engineering") == 0.0


class TestSimilarityCalculator:
    """Tests for SimilarityCalculator."""

    @pytest.mark.asyncio
    async def test_compute_all_basic(self) -> None:
        """Should compute all similarity metrics."""
        calc = SimilarityCalculator()

        scores = await calc.compute_all(
            title1="OpenAI GPT-5 Release",
            title2="OpenAI GPT-5 Announcement",
            summary1="OpenAI releases GPT-5 model",
            summary2="GPT-5 is released by OpenAI",
            tags1=["ai", "openai", "gpt"],
            tags2=["ai", "openai", "llm"],
            use_embedding=False,
        )

        assert "title" in scores
        assert "summary" in scores
        assert "tags" in scores
        assert "time" in scores
        assert "source" in scores
        assert "entity" in scores
        assert "embedding" in scores

        # Title should have high similarity
        assert scores["title"] > 0.3

    @pytest.mark.asyncio
    async def test_compute_all_with_times(self) -> None:
        """Should compute time overlap."""
        calc = SimilarityCalculator()
        now = datetime.now(timezone.utc)

        scores = await calc.compute_all(
            title1="Test",
            title2="Test",
            time1=now,
            time2=now - timedelta(hours=1),
            use_embedding=False,
        )

        assert scores["time"] > 0.9
