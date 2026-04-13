"""Tests for Timeline Repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.contracts.dto.memory import TimelineEventDTO, TimelinePointDTO
from app.memory.repositories.timeline_repository import TimelineRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def timeline_repo(mock_session):
    """Create a timeline repository with mock session."""
    return TimelineRepository(mock_session)


@pytest.fixture
def sample_timeline_point():
    """Create a sample timeline point."""
    return TimelinePointDTO(
        event_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        event_type="first_seen",
        title="Topic First Appeared",
        description="The topic was first detected in the system",
        source_item_id=123,
        source_type="news",
        importance_score=0.9,
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_timeline_event():
    """Create a sample timeline event DTO."""
    return TimelineEventDTO(
        id=1,
        topic_id=100,
        event_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        event_type="first_seen",
        title="Topic First Appeared",
        description="The topic was first detected in the system",
        source_item_id=123,
        source_type="news",
        importance_score=0.9,
        metadata={"source": "test"},
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestTimelineRepository:
    """Tests for TimelineRepository."""

    @pytest.mark.asyncio
    async def test_create_event(
        self, timeline_repo, mock_session, sample_timeline_point
    ):
        """Test creating a timeline event."""
        # Setup mock
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = sample_timeline_point.event_time
        mock_model.event_type = sample_timeline_point.event_type
        mock_model.title = sample_timeline_point.title
        mock_model.description = sample_timeline_point.description
        mock_model.source_item_id = sample_timeline_point.source_item_id
        mock_model.source_type = sample_timeline_point.source_type
        mock_model.importance_score = sample_timeline_point.importance_score
        mock_model.metadata_json = sample_timeline_point.metadata
        mock_model.created_at = datetime.now(timezone.utc)

        # Mock refresh to set model attributes
        async def mock_refresh(model):
            model.id = 1
            model.topic_id = 100
            model.event_time = sample_timeline_point.event_time
            model.event_type = sample_timeline_point.event_type
            model.title = sample_timeline_point.title
            model.description = sample_timeline_point.description
            model.source_item_id = sample_timeline_point.source_item_id
            model.source_type = sample_timeline_point.source_type
            model.importance_score = sample_timeline_point.importance_score
            model.metadata_json = sample_timeline_point.metadata
            model.created_at = datetime.now(timezone.utc)

        mock_session.refresh = mock_refresh

        # Execute
        with patch(
            "app.memory.repositories.timeline_repository.TopicTimelineEvent"
        ) as MockModel:
            MockModel.return_value = mock_model
            result = await timeline_repo.create_event(sample_timeline_point, 100)

        # Verify
        mock_session.add.assert_called_once()
        assert result.title == sample_timeline_point.title
        assert result.event_type == sample_timeline_point.event_type

    @pytest.mark.asyncio
    async def test_bulk_create_events(
        self, timeline_repo, mock_session, sample_timeline_point
    ):
        """Test bulk creating timeline events."""
        events = [sample_timeline_point, sample_timeline_point]

        # Setup mock models
        mock_models = []
        for i, e in enumerate(events):
            mock_model = MagicMock()
            mock_model.id = i + 1
            mock_model.topic_id = 100
            mock_model.event_time = e.event_time
            mock_model.event_type = e.event_type
            mock_model.title = e.title
            mock_model.description = e.description
            mock_model.source_item_id = e.source_item_id
            mock_model.source_type = e.source_type
            mock_model.importance_score = e.importance_score
            mock_model.metadata_json = e.metadata
            mock_model.created_at = datetime.now(timezone.utc)
            mock_models.append(mock_model)

        with patch(
            "app.memory.repositories.timeline_repository.TopicTimelineEvent"
        ) as MockModel:
            MockModel.side_effect = mock_models
            result = await timeline_repo.bulk_create_events(events, 100)

        # Verify
        mock_session.add_all.assert_called_once()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_bulk_create_events_empty(self, timeline_repo, mock_session):
        """Test bulk creating with empty list."""
        result = await timeline_repo.bulk_create_events([], 100)
        assert result == []
        mock_session.add_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_by_topic(self, timeline_repo, mock_session):
        """Test listing events by topic."""
        # Setup mock result
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.event_type = "first_seen"
        mock_model.title = "Test Event"
        mock_model.description = "Test description"
        mock_model.source_item_id = 123
        mock_model.source_type = "news"
        mock_model.importance_score = 0.8
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.list_by_topic(100, limit=50)

        # Verify
        assert len(result) == 1
        assert result[0].topic_id == 100
        assert result[0].event_type == "first_seen"

    @pytest.mark.asyncio
    async def test_list_by_time_range(self, timeline_repo, mock_session):
        """Test listing events by time range."""
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 31, tzinfo=timezone.utc)

        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.event_type = "release_published"
        mock_model.title = "Release Event"
        mock_model.description = "A release was published"
        mock_model.source_item_id = 456
        mock_model.source_type = "github"
        mock_model.importance_score = 0.7
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.list_by_time_range(100, start_time, end_time)

        # Verify
        assert len(result) == 1
        assert result[0].event_type == "release_published"

    @pytest.mark.asyncio
    async def test_list_milestones(self, timeline_repo, mock_session):
        """Test listing milestone events."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.event_type = "first_seen"
        mock_model.title = "Milestone Event"
        mock_model.description = "Important milestone"
        mock_model.source_item_id = 789
        mock_model.source_type = "news"
        mock_model.importance_score = 0.95
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.list_milestones(100, limit=20)

        # Verify
        assert len(result) == 1
        assert result[0].importance_score == 0.95

    @pytest.mark.asyncio
    async def test_delete_by_topic(self, timeline_repo, mock_session):
        """Test deleting events by topic."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute.return_value = mock_result

        # Execute
        count = await timeline_repo.delete_by_topic(100)

        # Verify
        assert count == 5
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_event(self, timeline_repo, mock_session):
        """Test getting the latest event."""
        mock_model = MagicMock()
        mock_model.id = 5
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 20, tzinfo=timezone.utc)
        mock_model.event_type = "topic_summary_changed"
        mock_model.title = "Latest Event"
        mock_model.description = "Most recent event"
        mock_model.source_item_id = None
        mock_model.source_type = None
        mock_model.importance_score = 0.5
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.get_latest_event(100)

        # Verify
        assert result is not None
        assert result.title == "Latest Event"

    @pytest.mark.asyncio
    async def test_get_latest_event_not_found(self, timeline_repo, mock_session):
        """Test getting latest event when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.get_latest_event(999)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_first_event(self, timeline_repo, mock_session):
        """Test getting the first event."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_model.event_type = "first_seen"
        mock_model.title = "First Event"
        mock_model.description = "The first event"
        mock_model.source_item_id = 100
        mock_model.source_type = "news"
        mock_model.importance_score = 1.0
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.get_first_event(100)

        # Verify
        assert result is not None
        assert result.title == "First Event"
        assert result.event_type == "first_seen"

    @pytest.mark.asyncio
    async def test_list_by_event_type(self, timeline_repo, mock_session):
        """Test listing events by type."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.topic_id = 100
        mock_model.event_time = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.event_type = "paper_published"
        mock_model.title = "Paper Event"
        mock_model.description = "A paper was published"
        mock_model.source_item_id = 200
        mock_model.source_type = "arxiv"
        mock_model.importance_score = 0.85
        mock_model.metadata_json = {}
        mock_model.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await timeline_repo.list_by_event_type(100, "paper_published")

        # Verify
        assert len(result) == 1
        assert result[0].event_type == "paper_published"
