"""Tests for Topic Memory Repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.dto.memory import (
    TopicMemoryCreateDTO,
    TopicMemoryDTO,
    TopicSnapshotCreateDTO,
    TopicSnapshotDTO,
)
from app.memory.repositories.topic_memory_repository import TopicMemoryRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def topic_memory_repo(mock_session):
    """Create a topic memory repository with mock session."""
    return TopicMemoryRepository(mock_session)


@pytest.fixture
def sample_topic_memory_create():
    """Create a sample topic memory create DTO."""
    return TopicMemoryCreateDTO(
        topic_id=100,
        first_seen_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        historical_status="new",
        current_stage="emerging",
        history_summary="A new topic about AI developments",
    )


@pytest.fixture
def sample_topic_snapshot_create():
    """Create a sample topic snapshot create DTO."""
    return TopicSnapshotCreateDTO(
        topic_id=100,
        summary="Current state of the topic",
        why_it_matters="Important for AI research",
        system_judgement="worth_tracking",
        heat_score=0.8,
        trend_score=0.7,
        item_count=15,
        source_count=5,
        representative_item_id=123,
    )


class TestTopicMemoryRepository:
    """Tests for TopicMemoryRepository."""

    @pytest.mark.asyncio
    async def test_get_by_topic_id_found(self, topic_memory_repo, mock_session):
        """Test getting topic memory by ID when found."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.first_seen_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_model.last_seen_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.historical_status = "evolving"
        mock_model.current_stage = "growing"
        mock_model.history_summary = "Topic has been evolving"
        mock_model.key_milestones_json = [{"date": "2024-01-10", "event": "Major update"}]
        mock_model.last_refreshed_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.metadata_json = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.get_by_topic_id(100)

        # Verify
        assert result is not None
        assert result.topic_id == 100
        assert result.historical_status == "evolving"
        assert len(result.key_milestones) == 1

    @pytest.mark.asyncio
    async def test_get_by_topic_id_not_found(self, topic_memory_repo, mock_session):
        """Test getting topic memory by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.get_by_topic_id(999)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_create(
        self, topic_memory_repo, mock_session, sample_topic_memory_create
    ):
        """Test creating topic memory."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = sample_topic_memory_create.topic_id
        mock_model.first_seen_at = sample_topic_memory_create.first_seen_at
        mock_model.last_seen_at = datetime.now(timezone.utc)
        mock_model.historical_status = sample_topic_memory_create.historical_status
        mock_model.current_stage = sample_topic_memory_create.current_stage
        mock_model.history_summary = sample_topic_memory_create.history_summary
        mock_model.key_milestones_json = []
        mock_model.last_refreshed_at = datetime.now(timezone.utc)
        mock_model.metadata_json = {}

        async def mock_refresh(model):
            for attr in dir(mock_model):
                if not attr.startswith("_"):
                    try:
                        setattr(model, attr, getattr(mock_model, attr))
                    except AttributeError:
                        pass

        mock_session.refresh = mock_refresh

        # Execute
        result = await topic_memory_repo.create(sample_topic_memory_create)

        # Verify
        mock_session.add.assert_called_once()
        assert result.topic_id == 100
        assert result.historical_status == "new"

    @pytest.mark.asyncio
    async def test_update(self, topic_memory_repo, mock_session):
        """Test updating topic memory."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.first_seen_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_model.last_seen_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.historical_status = "new"
        mock_model.current_stage = "emerging"
        mock_model.history_summary = "Original summary"
        mock_model.key_milestones_json = []
        mock_model.last_refreshed_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.metadata_json = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        update_data = {
            "historical_status": "evolving",
            "history_summary": "Updated summary",
        }
        result = await topic_memory_repo.update(100, update_data)

        # Verify
        assert result is not None
        assert mock_model.historical_status == "evolving"
        assert mock_model.history_summary == "Updated summary"

    @pytest.mark.asyncio
    async def test_update_not_found(self, topic_memory_repo, mock_session):
        """Test updating topic memory when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.update(999, {"historical_status": "evolving"})

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_create_snapshot(
        self, topic_memory_repo, mock_session, sample_topic_snapshot_create
    ):
        """Test creating a topic snapshot."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = sample_topic_snapshot_create.topic_id
        mock_model.snapshot_at = datetime.now(timezone.utc)
        mock_model.summary = sample_topic_snapshot_create.summary
        mock_model.why_it_matters = sample_topic_snapshot_create.why_it_matters
        mock_model.system_judgement = sample_topic_snapshot_create.system_judgement
        mock_model.heat_score = sample_topic_snapshot_create.heat_score
        mock_model.trend_score = sample_topic_snapshot_create.trend_score
        mock_model.item_count = sample_topic_snapshot_create.item_count
        mock_model.source_count = sample_topic_snapshot_create.source_count
        mock_model.representative_item_id = sample_topic_snapshot_create.representative_item_id
        mock_model.timeline_json = []
        mock_model.metadata_json = {}

        async def mock_refresh(model):
            for attr in dir(mock_model):
                if not attr.startswith("_"):
                    try:
                        setattr(model, attr, getattr(mock_model, attr))
                    except AttributeError:
                        pass

        mock_session.refresh = mock_refresh

        # Execute
        result = await topic_memory_repo.create_snapshot(sample_topic_snapshot_create)

        # Verify
        mock_session.add.assert_called_once()
        assert result.topic_id == 100
        assert result.summary == "Current state of the topic"

    @pytest.mark.asyncio
    async def test_list_snapshots(self, topic_memory_repo, mock_session):
        """Test listing snapshots for a topic."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.snapshot_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.summary = "Snapshot summary"
        mock_model.why_it_matters = "Important"
        mock_model.system_judgement = "worth_tracking"
        mock_model.heat_score = 0.8
        mock_model.trend_score = 0.7
        mock_model.item_count = 10
        mock_model.source_count = 3
        mock_model.representative_item_id = 123
        mock_model.timeline_json = []
        mock_model.metadata_json = {}

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.list_snapshots(100, limit=10)

        # Verify
        assert len(result) == 1
        assert result[0].topic_id == 100
        assert result[0].summary == "Snapshot summary"

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, topic_memory_repo, mock_session):
        """Test getting the latest snapshot."""
        mock_model = MagicMock()
        mock_model.id = 5
        mock_model.topic_id = 100
        mock_model.snapshot_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
        mock_model.summary = "Latest snapshot"
        mock_model.why_it_matters = "Very important"
        mock_model.system_judgement = "high_priority"
        mock_model.heat_score = 0.9
        mock_model.trend_score = 0.85
        mock_model.item_count = 25
        mock_model.source_count = 8
        mock_model.representative_item_id = 456
        mock_model.timeline_json = []
        mock_model.metadata_json = {}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.get_latest_snapshot(100)

        # Verify
        assert result is not None
        assert result.summary == "Latest snapshot"
        assert result.heat_score == 0.9

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_not_found(self, topic_memory_repo, mock_session):
        """Test getting latest snapshot when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await topic_memory_repo.get_latest_snapshot(999)

        # Verify
        assert result is None
