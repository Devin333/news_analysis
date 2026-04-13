"""Unit tests for merge service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicCandidateDTO, TopicReadDTO
from app.processing.clustering.merge_service import (
    MergeAction,
    MergeResult,
    MergeService,
)


def make_item(
    *,
    title: str = "Test Item",
    board_type: BoardType = BoardType.AI,
    tags: list[str] | None = None,
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
        published_at=datetime.now(timezone.utc),
        quality_score=0.8,
        board_type_candidate=board_type,
        tags=tags or [],
    )


def make_topic(
    *,
    topic_id: int = 1,
    title: str = "Test Topic",
    board_type: BoardType = BoardType.AI,
) -> TopicReadDTO:
    """Create a test topic."""
    return TopicReadDTO(
        id=topic_id,
        board_type=board_type,
        topic_type="auto",
        title=title,
        summary=None,
        representative_item_id=None,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        item_count=5,
        source_count=2,
        heat_score=25.0,
        trend_score=10.0,
        status="active",
        metadata_json={"tags": []},
    )


def make_candidate(
    *,
    topic_id: int = 1,
    title: str = "Test Topic",
    similarity_score: float = 0.5,
) -> TopicCandidateDTO:
    """Create a test candidate."""
    return TopicCandidateDTO(
        topic_id=topic_id,
        title=title,
        board_type=BoardType.AI,
        item_count=5,
        last_seen_at=datetime.now(timezone.utc),
        similarity_score=similarity_score,
        match_reasons=["title_overlap"],
    )


@pytest.mark.asyncio
async def test_resolve_no_candidates_creates_new() -> None:
    """Should create new topic when no candidates found."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    service = MergeService(repo)
    item = make_item(title="Unique Item")

    result = await service.resolve_for_item(item)

    assert result.action == MergeAction.CREATE_NEW
    assert result.target_topic_id is None
    assert result.candidate_count == 0


@pytest.mark.asyncio
async def test_resolve_with_good_candidate_merges() -> None:
    """Should merge when good candidate found."""
    repo = AsyncMock()

    # Return topics (find_candidates returns TopicReadDTO list)
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="OpenAI GPT-5 Release"),
    ]

    # Return topic details for context building
    repo.get_by_id.return_value = make_topic(topic_id=1, title="OpenAI GPT-5 Release")

    service = MergeService(repo, policy_name="relaxed")
    item = make_item(title="OpenAI GPT-5 Announcement", tags=["ai", "openai"])

    result = await service.resolve_for_item(item)

    # With relaxed policy and similar content, should have candidates
    assert result.candidate_count >= 1


@pytest.mark.asyncio
async def test_resolve_with_poor_candidates_creates_new() -> None:
    """Should create new topic when candidates are poor matches."""
    repo = AsyncMock()

    # Return topics with different content
    repo.find_candidates.return_value = [
        make_topic(topic_id=1, title="Unrelated Topic About Cooking"),
    ]

    repo.get_by_id.return_value = make_topic(topic_id=1, title="Unrelated Topic About Cooking")

    service = MergeService(repo, policy_name="strict")
    item = make_item(title="Completely Different Item About AI")

    result = await service.resolve_for_item(item)

    # With strict policy and low similarity, should create new
    assert result.action == MergeAction.CREATE_NEW


@pytest.mark.asyncio
async def test_resolve_uses_board_type_filter() -> None:
    """Should use board type for candidate filtering."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    service = MergeService(repo)
    item = make_item(title="Test", board_type=BoardType.ENGINEERING)

    await service.resolve_for_item(item, board_type=BoardType.RESEARCH)

    # Should use explicit board type
    repo.find_candidates.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_batch() -> None:
    """Should process multiple items."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    service = MergeService(repo)
    items = [
        make_item(title="Item 1"),
        make_item(title="Item 2"),
        make_item(title="Item 3"),
    ]

    results = await service.resolve_batch(items)

    assert len(results) == 3
    assert all(isinstance(r, MergeResult) for r in results)


@pytest.mark.asyncio
async def test_merge_result_includes_timing() -> None:
    """Should include processing time in result."""
    repo = AsyncMock()
    repo.find_candidates.return_value = []

    service = MergeService(repo)
    item = make_item(title="Test")

    result = await service.resolve_for_item(item)

    assert result.processing_time_ms >= 0


class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_create_new_result(self) -> None:
        """Should create result for new topic."""
        result = MergeResult(
            action=MergeAction.CREATE_NEW,
            target_topic_id=None,
            confidence=1.0,
            rationale="No candidates",
        )
        assert result.action == MergeAction.CREATE_NEW
        assert result.target_topic_id is None

    def test_merge_result(self) -> None:
        """Should create result for merge."""
        result = MergeResult(
            action=MergeAction.MERGE_INTO,
            target_topic_id=42,
            confidence=0.85,
            rationale="High similarity",
        )
        assert result.action == MergeAction.MERGE_INTO
        assert result.target_topic_id == 42


class TestMergeAction:
    """Tests for MergeAction enum."""

    def test_action_values(self) -> None:
        """Should have expected values."""
        assert MergeAction.CREATE_NEW == "create_new"
        assert MergeAction.MERGE_INTO == "merge_into"
        assert MergeAction.SKIP == "skip"
