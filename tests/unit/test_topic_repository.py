"""Unit tests for topic repository."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.common.enums import BoardType
from app.contracts.dto.topic import TopicCreateDTO
from app.storage.db.models.topic import Topic
from app.storage.repositories.topic_repository import TopicRepository


@pytest.mark.asyncio
async def test_create_topic() -> None:
    """Repository create should return TopicReadDTO."""
    session = AsyncMock()
    session.add = MagicMock()
    repo = TopicRepository(session)

    async def _flush_side_effect() -> None:
        added = session.add.call_args.args[0]
        added.id = 1
        added.heat_score = Decimal("0.0")
        added.trend_score = Decimal("0.0")

    session.flush.side_effect = _flush_side_effect

    data = TopicCreateDTO(
        board_type=BoardType.AI,
        topic_type="auto",
        title="Test Topic",
        summary="Test summary",
    )

    result = await repo.create(data)

    assert result.id == 1
    assert result.title == "Test Topic"
    assert result.board_type == BoardType.AI
    assert result.topic_type == "auto"
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found() -> None:
    """Repository should return None when topic does not exist."""
    session = AsyncMock()
    repo = TopicRepository(session)

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute.return_value = execute_result

    result = await repo.get_by_id(999)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_topic() -> None:
    """Repository should return topic when found."""
    session = AsyncMock()
    repo = TopicRepository(session)

    topic = Topic(
        board_type="ai",
        topic_type="auto",
        title="Found Topic",
        summary="Summary",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        item_count=5,
        source_count=3,
        heat_score=Decimal("25.5"),
        trend_score=Decimal("10.0"),
        status="active",
        metadata_json={},
    )
    topic.id = 10

    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = topic
    session.execute.return_value = execute_result

    result = await repo.get_by_id(10)

    assert result is not None
    assert result.id == 10
    assert result.title == "Found Topic"
    assert result.board_type == BoardType.AI
    assert result.item_count == 5


@pytest.mark.asyncio
async def test_list_recent_topics() -> None:
    """Repository should list recent topics."""
    session = AsyncMock()
    repo = TopicRepository(session)

    now = datetime.now(timezone.utc)
    topics = [
        Topic(
            board_type="ai",
            topic_type="auto",
            title=f"Topic {i}",
            summary=None,
            first_seen_at=now,
            last_seen_at=now,
            item_count=i,
            source_count=1,
            heat_score=Decimal("10.0"),
            trend_score=Decimal("5.0"),
            status="active",
            metadata_json={},
        )
        for i in range(3)
    ]
    for i, t in enumerate(topics):
        t.id = i + 1

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = topics
    session.execute.return_value = execute_result

    result = await repo.list_recent(limit=10)

    assert len(result) == 3
    assert result[0].title == "Topic 0"


@pytest.mark.asyncio
async def test_add_item_to_topic() -> None:
    """Repository should add item to topic."""
    session = AsyncMock()
    session.add = MagicMock()
    repo = TopicRepository(session)

    result = await repo.add_item(1, 100, link_reason="similarity")

    assert result is True
    session.add.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_topic_items() -> None:
    """Repository should return item IDs for topic."""
    session = AsyncMock()
    repo = TopicRepository(session)

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [101, 102, 103]
    session.execute.return_value = execute_result

    result = await repo.get_topic_items(1, limit=10)

    assert result == [101, 102, 103]


@pytest.mark.asyncio
async def test_update_metrics() -> None:
    """Repository should update topic metrics."""
    session = AsyncMock()
    repo = TopicRepository(session)

    execute_result = MagicMock()
    execute_result.rowcount = 1
    session.execute.return_value = execute_result

    result = await repo.update_metrics(
        1,
        item_count=10,
        source_count=5,
        heat_score=50.0,
    )

    assert result is True
    session.execute.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_metrics_no_values() -> None:
    """Repository should return False when no values to update."""
    session = AsyncMock()
    repo = TopicRepository(session)

    result = await repo.update_metrics(1)

    assert result is False
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_count_items() -> None:
    """Repository should count items in topic."""
    session = AsyncMock()
    repo = TopicRepository(session)

    execute_result = MagicMock()
    execute_result.scalar_one.return_value = 42
    session.execute.return_value = execute_result

    result = await repo.count_items(1)

    assert result == 42


@pytest.mark.asyncio
async def test_find_candidates() -> None:
    """Repository should find candidate topics."""
    session = AsyncMock()
    repo = TopicRepository(session)

    now = datetime.now(timezone.utc)
    topics = [
        Topic(
            board_type="ai",
            topic_type="auto",
            title="Candidate Topic",
            summary=None,
            first_seen_at=now,
            last_seen_at=now,
            item_count=5,
            source_count=2,
            heat_score=Decimal("30.0"),
            trend_score=Decimal("15.0"),
            status="active",
            metadata_json={},
        )
    ]
    topics[0].id = 1

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = topics
    session.execute.return_value = execute_result

    result = await repo.find_candidates(board_type=BoardType.AI, days=7, limit=50)

    assert len(result) == 1
    assert result[0].title == "Candidate Topic"


@pytest.mark.asyncio
async def test_update_summary() -> None:
    """Repository should update topic summary."""
    session = AsyncMock()
    repo = TopicRepository(session)

    execute_result = MagicMock()
    execute_result.rowcount = 1
    session.execute.return_value = execute_result

    result = await repo.update_summary(1, summary="New summary", representative_item_id=100)

    assert result is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_summary_no_values() -> None:
    """Repository should return False when no values to update."""
    session = AsyncMock()
    repo = TopicRepository(session)

    result = await repo.update_summary(1)

    assert result is False
    session.execute.assert_not_called()
