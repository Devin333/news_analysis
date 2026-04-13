"""Unit tests for merge scorer and policies."""

from datetime import datetime, timedelta, timezone

import pytest

from app.processing.clustering.merge_scorer import (
    ItemContext,
    MergeScoreResult,
    MergeScorer,
    MergeWeights,
    TopicContext,
)
from app.processing.clustering.policies import (
    MergeDecision,
    MergePolicy,
    MultiSignalPolicy,
    PolicyResult,
    RelaxedMergePolicy,
    StrictMergePolicy,
    get_policy,
)


class TestMergeWeights:
    """Tests for MergeWeights."""

    def test_default_weights_sum_to_one(self) -> None:
        """Default weights should sum to 1.0."""
        weights = MergeWeights()
        total = (
            weights.title
            + weights.embedding
            + weights.tags
            + weights.time
            + weights.source
            + weights.entity
        )
        assert total == pytest.approx(1.0)

    def test_custom_weights(self) -> None:
        """Should accept custom weights."""
        weights = MergeWeights(title=0.5, embedding=0.5, tags=0.0, time=0.0, source=0.0, entity=0.0)
        assert weights.title == 0.5
        assert weights.embedding == 0.5


class TestItemContext:
    """Tests for ItemContext."""

    def test_create_minimal(self) -> None:
        """Should create with minimal fields."""
        ctx = ItemContext(title="Test Title")
        assert ctx.title == "Test Title"
        assert ctx.summary is None
        assert ctx.tags == []

    def test_create_full(self) -> None:
        """Should create with all fields."""
        ctx = ItemContext(
            title="Test",
            summary="Summary",
            tags=["ai", "ml"],
            published_at=datetime.now(timezone.utc),
            source_id=1,
            entities=["OpenAI"],
            content_type="article",
            board_type="ai",
        )
        assert ctx.title == "Test"
        assert len(ctx.tags) == 2


class TestTopicContext:
    """Tests for TopicContext."""

    def test_create_minimal(self) -> None:
        """Should create with minimal fields."""
        ctx = TopicContext(topic_id=1, title="Test Topic")
        assert ctx.topic_id == 1
        assert ctx.title == "Test Topic"
        assert ctx.item_count == 0


class TestMergeScorer:
    """Tests for MergeScorer."""

    @pytest.mark.asyncio
    async def test_score_candidate_high_similarity(self) -> None:
        """Should score high for similar content."""
        scorer = MergeScorer()

        item = ItemContext(
            title="OpenAI releases GPT-5",
            summary="OpenAI has released GPT-5 model",
            tags=["ai", "openai", "gpt"],
        )

        topic = TopicContext(
            topic_id=1,
            title="OpenAI GPT-5 Announcement",
            summary="GPT-5 announced by OpenAI",
            tags=["ai", "openai", "llm"],
        )

        result = await scorer.score_candidate(item, topic, use_embedding=False)

        assert result.topic_id == 1
        assert result.total_score >= 0.3
        assert "title" in result.component_scores

    @pytest.mark.asyncio
    async def test_score_candidate_low_similarity(self) -> None:
        """Should score low for different content."""
        scorer = MergeScorer()

        item = ItemContext(
            title="Apple announces new iPhone",
            tags=["apple", "iphone"],
        )

        topic = TopicContext(
            topic_id=1,
            title="Google releases Android update",
            tags=["google", "android"],
        )

        result = await scorer.score_candidate(item, topic, use_embedding=False)

        assert result.total_score < 0.3
        assert not result.should_merge

    @pytest.mark.asyncio
    async def test_score_candidates_sorted(self) -> None:
        """Should return candidates sorted by score."""
        scorer = MergeScorer()

        item = ItemContext(title="OpenAI GPT-5", tags=["ai", "openai"])

        topics = [
            TopicContext(topic_id=1, title="Unrelated Topic", tags=["web"]),
            TopicContext(topic_id=2, title="OpenAI GPT-5 News", tags=["ai", "openai"]),
            TopicContext(topic_id=3, title="AI News", tags=["ai"]),
        ]

        results = await scorer.score_candidates(item, topics, use_embedding=False)

        assert len(results) == 3
        # Should be sorted by score descending
        assert results[0].total_score >= results[1].total_score >= results[2].total_score
        # Best match should be topic 2
        assert results[0].topic_id == 2

    @pytest.mark.asyncio
    async def test_find_best_merge_returns_best(self) -> None:
        """Should return best merge candidate."""
        scorer = MergeScorer(merge_threshold=0.2)

        item = ItemContext(title="OpenAI GPT-5", tags=["ai", "openai"])

        topics = [
            TopicContext(topic_id=1, title="OpenAI GPT-5 Release", tags=["ai", "openai"]),
        ]

        result = await scorer.find_best_merge(item, topics, use_embedding=False)

        assert result is not None
        assert result.topic_id == 1

    @pytest.mark.asyncio
    async def test_find_best_merge_returns_none_below_threshold(self) -> None:
        """Should return None if no candidate meets threshold."""
        scorer = MergeScorer(merge_threshold=0.9)

        item = ItemContext(title="Test Item")
        topics = [TopicContext(topic_id=1, title="Different Topic")]

        result = await scorer.find_best_merge(item, topics, use_embedding=False)

        assert result is None

    @pytest.mark.asyncio
    async def test_to_candidate_score_dto(self) -> None:
        """Should convert to DTO correctly."""
        scorer = MergeScorer()

        item = ItemContext(title="Test", tags=["ai"])
        topic = TopicContext(topic_id=1, title="Test Topic", tags=["ai"])

        result = await scorer.score_candidate(item, topic, use_embedding=False)
        dto = scorer.to_candidate_score_dto(result)

        assert dto.topic_id == 1
        assert dto.title == "Test Topic"
        assert dto.total_score == result.total_score


class TestMergePolicy:
    """Tests for MergePolicy."""

    def test_evaluate_no_candidates(self) -> None:
        """Should return MUST_CREATE for no candidates."""
        policy = MergePolicy()
        result = policy.evaluate([])

        assert result.decision == MergeDecision.MUST_CREATE
        assert result.target_topic_id is None

    def test_evaluate_low_score(self) -> None:
        """Should return MUST_CREATE for low scores."""
        policy = MergePolicy(must_create_threshold=0.3)

        results = [
            MergeScoreResult(
                topic_id=1,
                topic_title="Test",
                total_score=0.1,
                component_scores={},
                should_merge=False,
                confidence=0.2,
                rationale="",
            )
        ]

        result = policy.evaluate(results)
        assert result.decision == MergeDecision.MUST_CREATE

    def test_evaluate_high_score(self) -> None:
        """Should return LIKELY_MERGE for high scores."""
        policy = MergePolicy(likely_merge_threshold=0.5, min_confidence=0.5)

        results = [
            MergeScoreResult(
                topic_id=1,
                topic_title="Test",
                total_score=0.7,
                component_scores={},
                should_merge=True,
                confidence=0.8,
                rationale="",
            )
        ]

        result = policy.evaluate(results)
        assert result.decision == MergeDecision.LIKELY_MERGE
        assert result.target_topic_id == 1

    def test_evaluate_uncertain(self) -> None:
        """Should return UNCERTAIN for moderate scores."""
        policy = MergePolicy(
            uncertain_threshold=0.3,
            likely_merge_threshold=0.6,
        )

        results = [
            MergeScoreResult(
                topic_id=1,
                topic_title="Test",
                total_score=0.45,
                component_scores={},
                should_merge=False,
                confidence=0.5,
                rationale="",
            )
        ]

        result = policy.evaluate(results)
        assert result.decision == MergeDecision.UNCERTAIN


class TestStrictMergePolicy:
    """Tests for StrictMergePolicy."""

    def test_higher_thresholds(self) -> None:
        """Should have higher thresholds than default."""
        strict = StrictMergePolicy()
        default = MergePolicy()

        assert strict._likely_merge_threshold > default._likely_merge_threshold
        assert strict._min_confidence > default._min_confidence


class TestRelaxedMergePolicy:
    """Tests for RelaxedMergePolicy."""

    def test_lower_thresholds(self) -> None:
        """Should have lower thresholds than default."""
        relaxed = RelaxedMergePolicy()
        default = MergePolicy()

        assert relaxed._likely_merge_threshold < default._likely_merge_threshold
        assert relaxed._min_confidence < default._min_confidence


class TestMultiSignalPolicy:
    """Tests for MultiSignalPolicy."""

    def test_requires_multiple_signals(self) -> None:
        """Should require multiple strong signals."""
        policy = MultiSignalPolicy(min_strong_signals=2, strong_signal_threshold=0.5)

        # Only one strong signal
        results = [
            MergeScoreResult(
                topic_id=1,
                topic_title="Test",
                total_score=0.6,
                component_scores={"title": 0.8, "tags": 0.2, "time": 0.3},
                should_merge=True,
                confidence=0.7,
                rationale="",
            )
        ]

        result = policy.evaluate(results)
        # Should not merge with only one strong signal
        assert result.decision != MergeDecision.LIKELY_MERGE

    def test_merges_with_multiple_signals(self) -> None:
        """Should merge with multiple strong signals."""
        policy = MultiSignalPolicy(min_strong_signals=2, strong_signal_threshold=0.5)

        # Two strong signals
        results = [
            MergeScoreResult(
                topic_id=1,
                topic_title="Test",
                total_score=0.7,
                component_scores={"title": 0.8, "tags": 0.7, "time": 0.3},
                should_merge=True,
                confidence=0.8,
                rationale="",
            )
        ]

        result = policy.evaluate(results)
        assert result.decision == MergeDecision.LIKELY_MERGE


class TestGetPolicy:
    """Tests for get_policy function."""

    def test_get_default_policy(self) -> None:
        """Should return default policy."""
        policy = get_policy("default")
        assert isinstance(policy, MergePolicy)

    def test_get_strict_policy(self) -> None:
        """Should return strict policy."""
        policy = get_policy("strict")
        assert isinstance(policy, StrictMergePolicy)

    def test_get_relaxed_policy(self) -> None:
        """Should return relaxed policy."""
        policy = get_policy("relaxed")
        assert isinstance(policy, RelaxedMergePolicy)

    def test_get_multi_signal_policy(self) -> None:
        """Should return multi-signal policy."""
        policy = get_policy("multi_signal")
        assert isinstance(policy, MultiSignalPolicy)

    def test_unknown_policy_raises(self) -> None:
        """Should raise for unknown policy."""
        with pytest.raises(ValueError, match="Unknown policy"):
            get_policy("unknown")
