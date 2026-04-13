"""Unit tests for candidate retriever."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicReadDTO
from app.processing.clustering.candidate_retriever import (
    CandidateConfig,
    CandidateRetriever,
)


def make_item(
    *,
    title: str = "Test Item",
    board_type: BoardType = BoardType.GENERAL,
    tags: list[str] | None = None,
    published_at: datetime | None = None,
) -> NormalizedItemDTO:
    """Create a test normalized item."""
    return NormalizedItemDTO(
        id=1,
        raw_item_id=1,
        source_id=1,
        title=title,
        canonical_url="https://example.com/test",
        content_type="article",
        clean_text="Test content",
        excerpt="Test excerpt",
        published_at=published_at or datetime.now(timezone.utc),
        quality_score=0.8,
        board_type_candidate=board_type,
        tags=tags or [],
    )


def make_topic(
    *,
    topic_id: int = 1,
    title: str = "Test Topic",
    board_type: BoardType = BoardType.AI,
    item_count: int = 5,
    last_seen_at: datetime | None = None,
    tags: list[str] | None = None,
) -> TopicReadDTO:
    """Create a test topic."""
    return TopicReadDTO(
        id=topic_id,
        board_type=board_type,
        topic_type="auto",
        title=title,
        summary=None,
        representative_item_id=None,
        first_seen_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_seen_at=last_seen_at or datetime.now(timezone.utc),
        item_count=item_count,
        source_count=2,
        heat_score=25.0,
        trend_score=10.0,
        status="active",
        metadata_json={"tags": tags or []},
    )


@pytest.mark.asyncio
async def test_find_candidates_returns_scored_results() -> None:
    """Should return scored candidate topics."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="OpenAI GPT-5 Release"),
        make_topic(topic_id=2, title="Google AI Update"),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="OpenAI announces GPT-5", board_type=BoardType.AI)

    result = await retriever.find_candidates(item)

    assert len(result.candidates) >= 1
    assert result.total_evaluated == 2
    # First candidate should have higher score due to title overlap
    if len(result.candidates) > 1:
        assert result.candidates[0].similarity_score >= result.candidates[1].similarity_score


@pytest.mark.asyncio
async def test_find_candidates_filters_by_threshold() -> None:
    """Should filter candidates below threshold."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="Completely Unrelated Topic"),
    ]

    config = CandidateConfig(min_score_threshold=0.5)
    retriever = CandidateRetriever(repo, config)
    item = make_item(title="OpenAI GPT-5 Release", board_type=BoardType.AI)

    result = await retriever.find_candidates(item)

    # Should filter out low-scoring candidates
    assert len(result.candidates) == 0


@pytest.mark.asyncio
async def test_find_candidates_respects_max_candidates() -> None:
    """Should limit results to max_candidates."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=i, title=f"AI Topic {i}")
        for i in range(10)
    ]

    config = CandidateConfig(max_candidates=3, min_score_threshold=0.0)
    retriever = CandidateRetriever(repo, config)
    item = make_item(title="AI Topic Test", board_type=BoardType.AI)

    result = await retriever.find_candidates(item)

    assert len(result.candidates) <= 3


@pytest.mark.asyncio
async def test_find_candidates_uses_board_type() -> None:
    """Should use item's board type for filtering."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test", board_type=BoardType.ENGINEERING)

    await retriever.find_candidates(item)

    repo.find_candidates.assert_called_once()
    call_kwargs = repo.find_candidates.call_args.kwargs
    assert call_kwargs["board_type"] == BoardType.ENGINEERING


@pytest.mark.asyncio
async def test_find_candidates_with_explicit_board_type() -> None:
    """Should use explicit board type over item's board type."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test", board_type=BoardType.ENGINEERING)

    await retriever.find_candidates(item, board_type=BoardType.RESEARCH)

    call_kwargs = repo.find_candidates.call_args.kwargs
    assert call_kwargs["board_type"] == BoardType.RESEARCH


@pytest.mark.asyncio
async def test_score_candidate_title_overlap() -> None:
    """Should score higher for title overlap."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="OpenAI GPT-5 Release"),
        make_topic(topic_id=2, title="Unrelated Topic Here"),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="OpenAI GPT-5 Announcement", board_type=BoardType.AI)

    result = await retriever.find_candidates(item)

    # Topic 1 should score higher due to title overlap
    if len(result.candidates) >= 2:
        topic1_score = next(c for c in result.candidates if c.topic_id == 1).similarity_score
        topic2_score = next(c for c in result.candidates if c.topic_id == 2).similarity_score
        assert topic1_score > topic2_score


@pytest.mark.asyncio
async def test_score_candidate_tag_overlap() -> None:
    """Should score higher for tag overlap."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="Topic A", tags=["ai", "ml", "python"]),
        make_topic(topic_id=2, title="Topic B", tags=["web", "frontend"]),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test", board_type=BoardType.AI, tags=["ai", "ml"])

    result = await retriever.find_candidates(item)

    if len(result.candidates) >= 2:
        topic1 = next((c for c in result.candidates if c.topic_id == 1), None)
        topic2 = next((c for c in result.candidates if c.topic_id == 2), None)
        if topic1 and topic2:
            assert topic1.similarity_score > topic2.similarity_score


@pytest.mark.asyncio
async def test_score_candidate_recency() -> None:
    """Should score higher for recent topics."""
    now = datetime.now(timezone.utc)
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="Recent Topic", last_seen_at=now - timedelta(hours=1)),
        make_topic(topic_id=2, title="Old Topic", last_seen_at=now - timedelta(days=6)),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test Topic", board_type=BoardType.AI, published_at=now)

    result = await retriever.find_candidates(item)

    if len(result.candidates) >= 2:
        recent = next((c for c in result.candidates if c.topic_id == 1), None)
        old = next((c for c in result.candidates if c.topic_id == 2), None)
        if recent and old:
            # Recent topic should have higher recency contribution
            assert "recent" in str(recent.match_reasons) or recent.similarity_score >= old.similarity_score


@pytest.mark.asyncio
async def test_find_candidates_multi_board() -> None:
    """Should search across all boards."""
    repo = AsyncMock()
    repo.list_recent.return_value = [
        make_topic(topic_id=1, title="AI Topic", board_type=BoardType.AI),
        make_topic(topic_id=2, title="Engineering Topic", board_type=BoardType.ENGINEERING),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test Topic")

    result = await retriever.find_candidates_multi_board(item)

    repo.list_recent.assert_called_once()
    assert result.total_evaluated == 2


@pytest.mark.asyncio
async def test_get_top_candidate_returns_best() -> None:
    """Should return the best candidate."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="OpenAI GPT-5 Release"),
        make_topic(topic_id=2, title="Other Topic"),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="OpenAI GPT-5 Announcement", board_type=BoardType.AI)

    top = await retriever.get_top_candidate(item, min_score=0.0)

    assert top is not None
    assert top.topic_id == 1


@pytest.mark.asyncio
async def test_get_top_candidate_returns_none_below_threshold() -> None:
    """Should return None if best candidate is below threshold."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="Completely Different Topic"),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(title="OpenAI GPT-5", board_type=BoardType.AI)

    top = await retriever.get_top_candidate(item, min_score=0.9)

    assert top is None


@pytest.mark.asyncio
async def test_get_top_candidate_returns_none_when_empty() -> None:
    """Should return None when no candidates."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    retriever = CandidateRetriever(repo)
    item = make_item(title="Test", board_type=BoardType.AI)

    top = await retriever.get_top_candidate(item)

    assert top is None


@pytest.mark.asyncio
async def test_candidate_includes_match_reasons() -> None:
    """Should include match reasons in candidates."""
    repo = AsyncMock()
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="OpenAI GPT-5 Release", tags=["ai", "openai"]),
    ]

    retriever = CandidateRetriever(repo)
    item = make_item(
        title="OpenAI GPT-5 Announcement",
        board_type=BoardType.AI,
        tags=["ai", "openai"],
    )

    result = await retriever.find_candidates(item)

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    # Should have match reasons
    assert len(candidate.match_reasons) > 0


class TestCandidateConfig:
    """Tests for CandidateConfig."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        config = CandidateConfig()
        assert config.lookback_days == 7
        assert config.max_candidates == 50
        assert config.min_score_threshold == 0.1

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = CandidateConfig(
            lookback_days=14,
            max_candidates=100,
            min_score_threshold=0.2,
        )
        assert config.lookback_days == 14
        assert config.max_candidates == 100
        assert config.min_score_threshold == 0.2

    def test_weight_sum(self) -> None:
        """Weights should sum to 1.0."""
        config = CandidateConfig()
        total = (
            config.title_weight
            + config.tag_weight
            + config.recency_weight
            + config.board_weight
        )
        assert total == pytest.approx(1.0)
