"""Unit tests for summary builders."""

from datetime import datetime, timedelta, timezone

import pytest

from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicReadDTO
from app.editorial.summary_builders.representative_item_selector import (
    RepresentativeItemSelector,
    SelectionCriteria,
)
from app.editorial.summary_builders.topic_stub_builder import (
    TopicStubBuilder,
    TopicStub,
)


def make_item(
    *,
    item_id: int = 1,
    title: str = "Test Item",
    clean_text: str = "Test content " * 50,
    published_at: datetime | None = None,
    quality_score: float = 0.7,
    source_id: int = 1,
    tags: list[str] | None = None,
) -> NormalizedItemDTO:
    """Create a test normalized item."""
    return NormalizedItemDTO(
        id=item_id,
        raw_item_id=item_id,
        source_id=source_id,
        title=title,
        canonical_url=f"https://example.com/item/{item_id}",
        content_type="article",
        clean_text=clean_text,
        excerpt="Test excerpt",
        published_at=published_at or datetime.now(timezone.utc),
        quality_score=quality_score,
        board_type_candidate=BoardType.AI,
        tags=tags or [],
    )


def make_topic(
    *,
    topic_id: int = 1,
    title: str = "Test Topic",
    item_count: int = 5,
    source_count: int = 2,
) -> TopicReadDTO:
    """Create a test topic."""
    return TopicReadDTO(
        id=topic_id,
        board_type=BoardType.AI,
        topic_type="auto",
        title=title,
        summary=None,
        representative_item_id=None,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        item_count=item_count,
        source_count=source_count,
        heat_score=25.0,
        trend_score=10.0,
        status="active",
        metadata_json={},
    )


class TestRepresentativeItemSelector:
    """Tests for RepresentativeItemSelector."""

    def test_select_single_item(self) -> None:
        """Should return the only item."""
        selector = RepresentativeItemSelector()
        item = make_item()

        result = selector.select([item])

        assert result == item

    def test_select_empty_list(self) -> None:
        """Should return None for empty list."""
        selector = RepresentativeItemSelector()

        result = selector.select([])

        assert result is None

    def test_select_prefers_recent(self) -> None:
        """Should prefer more recent items."""
        selector = RepresentativeItemSelector(
            criteria=SelectionCriteria(recency_weight=1.0, quality_weight=0.0, length_weight=0.0, title_weight=0.0, source_trust_weight=0.0)
        )

        now = datetime.now(timezone.utc)
        old_item = make_item(item_id=1, published_at=now - timedelta(days=5))
        new_item = make_item(item_id=2, published_at=now - timedelta(hours=1))

        result = selector.select([old_item, new_item])

        assert result.id == 2

    def test_select_prefers_quality(self) -> None:
        """Should prefer higher quality items."""
        selector = RepresentativeItemSelector(
            criteria=SelectionCriteria(recency_weight=0.0, quality_weight=1.0, length_weight=0.0, title_weight=0.0, source_trust_weight=0.0)
        )

        low_quality = make_item(item_id=1, quality_score=0.3)
        high_quality = make_item(item_id=2, quality_score=0.9)

        result = selector.select([low_quality, high_quality])

        assert result.id == 2

    def test_select_with_source_trust(self) -> None:
        """Should consider source trust scores."""
        selector = RepresentativeItemSelector(
            criteria=SelectionCriteria(recency_weight=0.0, quality_weight=0.0, length_weight=0.0, title_weight=0.0, source_trust_weight=1.0)
        )

        item1 = make_item(item_id=1, source_id=1)
        item2 = make_item(item_id=2, source_id=2)

        trust_scores = {1: 0.3, 2: 0.9}
        result = selector.select([item1, item2], source_trust_scores=trust_scores)

        assert result.id == 2

    def test_score_items_returns_sorted(self) -> None:
        """Should return items sorted by score."""
        selector = RepresentativeItemSelector()

        items = [
            make_item(item_id=1, quality_score=0.3),
            make_item(item_id=2, quality_score=0.9),
            make_item(item_id=3, quality_score=0.6),
        ]

        scored = selector.score_items(items)

        assert len(scored) == 3
        assert scored[0].score >= scored[1].score >= scored[2].score

    def test_select_top_n(self) -> None:
        """Should return top N items."""
        selector = RepresentativeItemSelector()

        items = [make_item(item_id=i) for i in range(5)]

        result = selector.select_top_n(items, n=3)

        assert len(result) == 3


class TestSelectionCriteria:
    """Tests for SelectionCriteria."""

    def test_default_weights(self) -> None:
        """Should have sensible defaults."""
        criteria = SelectionCriteria()

        total = (
            criteria.recency_weight
            + criteria.quality_weight
            + criteria.length_weight
            + criteria.title_weight
            + criteria.source_trust_weight
        )
        assert total == pytest.approx(1.0)

    def test_custom_weights(self) -> None:
        """Should accept custom weights."""
        criteria = SelectionCriteria(recency_weight=0.5, quality_weight=0.5)
        assert criteria.recency_weight == 0.5


class TestTopicStubBuilder:
    """Tests for TopicStubBuilder."""

    def test_build_basic(self) -> None:
        """Should build basic topic stub."""
        builder = TopicStubBuilder()
        topic = make_topic(title="AI News Today")
        items = [make_item(item_id=1), make_item(item_id=2)]

        stub = builder.build(topic, items)

        assert stub.title == "AI News Today"
        assert stub.item_count == 2
        assert stub.representative_item_id is not None

    def test_build_empty_items(self) -> None:
        """Should handle empty items list."""
        builder = TopicStubBuilder()
        topic = make_topic(title="Empty Topic", item_count=0)

        stub = builder.build(topic, [])

        assert stub.title == "Empty Topic"
        assert stub.item_count == 0

    def test_build_extracts_common_tags(self) -> None:
        """Should extract common tags from items."""
        builder = TopicStubBuilder()
        topic = make_topic()
        items = [
            make_item(item_id=1, tags=["ai", "ml", "python"]),
            make_item(item_id=2, tags=["ai", "ml", "java"]),
            make_item(item_id=3, tags=["ai", "web"]),
        ]

        stub = builder.build(topic, items)

        assert "ai" in stub.common_tags
        assert "ml" in stub.common_tags

    def test_build_calculates_time_range(self) -> None:
        """Should calculate time range."""
        builder = TopicStubBuilder()
        topic = make_topic()

        now = datetime.now(timezone.utc)
        items = [
            make_item(item_id=1, published_at=now - timedelta(hours=2)),
            make_item(item_id=2, published_at=now - timedelta(hours=1)),
        ]

        stub = builder.build(topic, items)

        assert stub.time_range != ""

    def test_build_gets_key_sources(self) -> None:
        """Should get key source names."""
        builder = TopicStubBuilder()
        topic = make_topic()
        items = [
            make_item(item_id=1, source_id=1),
            make_item(item_id=2, source_id=1),
            make_item(item_id=3, source_id=2),
        ]

        source_names = {1: "TechCrunch", 2: "Wired"}
        stub = builder.build(topic, items, source_names=source_names)

        assert "TechCrunch" in stub.key_sources

    def test_build_from_items_only(self) -> None:
        """Should build stub from items only."""
        builder = TopicStubBuilder()
        items = [
            make_item(item_id=1, title="OpenAI GPT-5 Release"),
            make_item(item_id=2, title="GPT-5 Features"),
        ]

        stub = builder.build_from_items_only(items)

        assert stub.item_count == 2
        assert stub.source_count >= 1

    def test_build_from_items_only_empty(self) -> None:
        """Should handle empty items."""
        builder = TopicStubBuilder()

        stub = builder.build_from_items_only([])

        assert stub.title == "Empty Topic"
        assert stub.item_count == 0


class TestTopicStub:
    """Tests for TopicStub dataclass."""

    def test_create_stub(self) -> None:
        """Should create stub with all fields."""
        stub = TopicStub(
            title="Test Topic",
            summary="Test summary",
            item_count=5,
            source_count=2,
            time_range="过去24小时内",
            representative_item_id=1,
            key_sources=["Source A"],
            common_tags=["ai", "ml"],
        )

        assert stub.title == "Test Topic"
        assert stub.item_count == 5
        assert len(stub.common_tags) == 2
