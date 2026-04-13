"""Unit tests for clustering features."""

from datetime import datetime, timedelta, timezone

import pytest

from app.processing.clustering.features import (
    compute_content_type_similarity,
    compute_entity_overlap,
    compute_keyword_overlap,
    compute_recency_score,
    compute_source_similarity,
    compute_tag_overlap_score,
    compute_title_overlap_score,
    extract_keywords,
    tokenize,
)


class TestTokenize:
    """Tests for tokenize function."""

    def test_basic_tokenization(self) -> None:
        """Should split text into lowercase words."""
        result = tokenize("Hello World Test")
        assert result == {"hello", "world", "test"}

    def test_filters_short_tokens(self) -> None:
        """Should filter tokens shorter than 2 characters."""
        result = tokenize("I am a test")
        assert "i" not in result
        assert "a" not in result
        assert "am" in result
        assert "test" in result

    def test_handles_punctuation(self) -> None:
        """Should handle punctuation correctly."""
        result = tokenize("Hello, World! How are you?")
        assert "hello" in result
        assert "world" in result
        assert "how" in result

    def test_empty_string(self) -> None:
        """Should return empty set for empty string."""
        assert tokenize("") == set()

    def test_none_like_empty(self) -> None:
        """Should handle None-like input."""
        assert tokenize("") == set()


class TestTitleOverlapScore:
    """Tests for compute_title_overlap_score."""

    def test_identical_titles(self) -> None:
        """Identical titles should have high score."""
        score = compute_title_overlap_score(
            "OpenAI releases GPT-5",
            "OpenAI releases GPT-5",
        )
        assert score == 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap should have moderate score."""
        score = compute_title_overlap_score(
            "OpenAI releases GPT-5 model",
            "OpenAI announces GPT-5 launch",
        )
        assert 0.3 < score < 0.8

    def test_no_overlap(self) -> None:
        """No overlap should have zero score."""
        score = compute_title_overlap_score(
            "Apple announces new iPhone",
            "Google releases Android update",
        )
        assert score == 0.0

    def test_min_overlap_threshold(self) -> None:
        """Should respect minimum overlap threshold."""
        # Only one word overlaps
        score = compute_title_overlap_score(
            "OpenAI news today",
            "OpenAI different topic",
            min_overlap=2,
        )
        # "openai" overlaps but min_overlap=2 requires 2 words
        assert score == 0.0

    def test_empty_titles(self) -> None:
        """Empty titles should return zero."""
        assert compute_title_overlap_score("", "test") == 0.0
        assert compute_title_overlap_score("test", "") == 0.0


class TestTagOverlapScore:
    """Tests for compute_tag_overlap_score."""

    def test_identical_tags(self) -> None:
        """Identical tags should have score 1.0."""
        score = compute_tag_overlap_score(
            ["ai", "ml", "python"],
            ["ai", "ml", "python"],
        )
        assert score == 1.0

    def test_partial_overlap(self) -> None:
        """Partial overlap should have moderate score."""
        score = compute_tag_overlap_score(
            ["ai", "ml", "python"],
            ["ai", "ml", "java"],
        )
        # 2 out of 4 unique tags
        assert score == 0.5

    def test_no_overlap(self) -> None:
        """No overlap should have zero score."""
        score = compute_tag_overlap_score(
            ["ai", "ml"],
            ["web", "frontend"],
        )
        assert score == 0.0

    def test_empty_tags(self) -> None:
        """Empty tags should return zero."""
        assert compute_tag_overlap_score([], ["ai"]) == 0.0
        assert compute_tag_overlap_score(["ai"], []) == 0.0

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        score = compute_tag_overlap_score(
            ["AI", "ML"],
            ["ai", "ml"],
        )
        assert score == 1.0


class TestRecencyScore:
    """Tests for compute_recency_score."""

    def test_same_time(self) -> None:
        """Same time should have score 1.0."""
        now = datetime.now(timezone.utc)
        score = compute_recency_score(now, now)
        assert score == 1.0

    def test_recent_item(self) -> None:
        """Recent item should have high score."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        score = compute_recency_score(one_hour_ago, now, max_hours=168)
        assert score > 0.9

    def test_old_item(self) -> None:
        """Old item should have low score."""
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)
        score = compute_recency_score(one_week_ago, now, max_hours=168)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_beyond_max_hours(self) -> None:
        """Beyond max hours should return zero."""
        now = datetime.now(timezone.utc)
        two_weeks_ago = now - timedelta(days=14)
        score = compute_recency_score(two_weeks_ago, now, max_hours=168)
        assert score == 0.0

    def test_none_published_at(self) -> None:
        """None published_at should return neutral score."""
        now = datetime.now(timezone.utc)
        score = compute_recency_score(None, now)
        assert score == 0.5


class TestSourceSimilarity:
    """Tests for compute_source_similarity."""

    def test_same_source(self) -> None:
        """Same source should return 1.0."""
        score = compute_source_similarity(1, [1, 2, 3])
        assert score == 1.0

    def test_different_source(self) -> None:
        """Different source should return 0.0."""
        score = compute_source_similarity(4, [1, 2, 3])
        assert score == 0.0

    def test_none_source(self) -> None:
        """None source should return 0.0."""
        score = compute_source_similarity(None, [1, 2, 3])
        assert score == 0.0

    def test_empty_topic_sources(self) -> None:
        """Empty topic sources should return 0.0."""
        score = compute_source_similarity(1, [])
        assert score == 0.0


class TestContentTypeSimilarity:
    """Tests for compute_content_type_similarity."""

    def test_matching_type(self) -> None:
        """Matching type should have high score."""
        score = compute_content_type_similarity(
            "article",
            ["article", "article", "blog"],
        )
        assert score > 0.5

    def test_non_matching_type(self) -> None:
        """Non-matching type should return 0.0."""
        score = compute_content_type_similarity(
            "video",
            ["article", "blog"],
        )
        assert score == 0.0

    def test_none_type(self) -> None:
        """None type should return neutral score."""
        score = compute_content_type_similarity(None, ["article"])
        assert score == 0.5

    def test_empty_topic_types(self) -> None:
        """Empty topic types should return neutral score."""
        score = compute_content_type_similarity("article", [])
        assert score == 0.5


class TestExtractKeywords:
    """Tests for extract_keywords."""

    def test_basic_extraction(self) -> None:
        """Should extract keywords from text."""
        text = "Python machine learning deep learning neural networks"
        keywords = extract_keywords(text, top_n=5)
        assert "python" in keywords
        assert "machine" in keywords
        # "learning" appears twice so should be in top keywords
        assert "learning" in keywords or "neural" in keywords

    def test_filters_stop_words(self) -> None:
        """Should filter common stop words."""
        text = "The quick brown fox jumps over the lazy dog"
        keywords = extract_keywords(text, top_n=10)
        assert "the" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords

    def test_respects_top_n(self) -> None:
        """Should respect top_n limit."""
        text = "one two three four five six seven eight nine ten"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) <= 3


class TestKeywordOverlap:
    """Tests for compute_keyword_overlap."""

    def test_high_overlap(self) -> None:
        """High keyword overlap should have high score."""
        item_text = "Python machine learning deep learning"
        topic_keywords = ["python", "machine", "learning", "deep"]
        score = compute_keyword_overlap(item_text, topic_keywords)
        assert score > 0.5

    def test_no_overlap(self) -> None:
        """No overlap should return 0.0."""
        item_text = "JavaScript frontend web development"
        topic_keywords = ["python", "backend", "database"]
        score = compute_keyword_overlap(item_text, topic_keywords)
        assert score == 0.0

    def test_empty_inputs(self) -> None:
        """Empty inputs should return 0.0."""
        assert compute_keyword_overlap("", ["python"]) == 0.0
        assert compute_keyword_overlap("python", []) == 0.0


class TestEntityOverlap:
    """Tests for compute_entity_overlap."""

    def test_matching_entities(self) -> None:
        """Matching entities should have high score."""
        score = compute_entity_overlap(
            ["OpenAI", "GPT-5"],
            ["OpenAI", "GPT-5", "Microsoft"],
        )
        assert score > 0.5

    def test_no_matching_entities(self) -> None:
        """No matching entities should return 0.0."""
        score = compute_entity_overlap(
            ["Apple", "iPhone"],
            ["Google", "Android"],
        )
        assert score == 0.0

    def test_empty_entities(self) -> None:
        """Empty entities should return 0.0."""
        assert compute_entity_overlap([], ["OpenAI"]) == 0.0
        assert compute_entity_overlap(["OpenAI"], []) == 0.0

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        score = compute_entity_overlap(
            ["OPENAI", "GPT"],
            ["openai", "gpt"],
        )
        assert score == 1.0
