"""Tests for Entity Memory Repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.dto.memory import EntityMemoryCreateDTO, EntityMemoryDTO
from app.memory.repositories.entity_memory_repository import EntityMemoryRepository


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
def entity_memory_repo(mock_session):
    """Create an entity memory repository with mock session."""
    return EntityMemoryRepository(mock_session)


@pytest.fixture
def sample_entity_memory_create():
    """Create a sample entity memory create DTO."""
    return EntityMemoryCreateDTO(
        entity_id=50,
        summary="OpenAI is an AI research company",
        related_topic_ids=[100, 101, 102],
        milestones=[
            {"date": "2024-01-15", "event": "Released GPT-5"},
            {"date": "2024-02-01", "event": "Partnership announced"},
        ],
        recent_signals=["New product launch", "Executive change"],
    )


class TestEntityMemoryRepository:
    """Tests for EntityMemoryRepository."""

    @pytest.mark.asyncio
    async def test_get_by_entity_id_found(self, entity_memory_repo, mock_session):
        """Test getting entity memory by ID when found."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.entity_id = 50
        mock_model.summary = "OpenAI is an AI research company"
        mock_model.related_topic_ids_json = [100, 101, 102]
        mock_model.milestones_json = [{"date": "2024-01-15", "event": "Released GPT-5"}]
        mock_model.recent_signals_json = ["New product launch"]
        mock_model.last_refreshed_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
        mock_model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_model.updated_at = datetime(2024, 1, 20, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await entity_memory_repo.get_by_entity_id(50)

        # Verify
        assert result is not None
        assert result.entity_id == 50
        assert result.summary == "OpenAI is an AI research company"
        assert len(result.related_topic_ids) == 3

    @pytest.mark.asyncio
    async def test_get_by_entity_id_not_found(self, entity_memory_repo, mock_session):
        """Test getting entity memory by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await entity_memory_repo.get_by_entity_id(999)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_create_or_update_create(
        self, entity_memory_repo, mock_session, sample_entity_memory_create
    ):
        """Test creating entity memory when it doesn't exist."""
        # First call returns None (not found)
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None

        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.entity_id = sample_entity_memory_create.entity_id
        mock_model.summary = sample_entity_memory_create.summary
        mock_model.related_topic_ids_json = sample_entity_memory_create.related_topic_ids
        mock_model.milestones_json = sample_entity_memory_create.milestones
        mock_model.recent_signals_json = sample_entity_memory_create.recent_signals
        mock_model.last_refreshed_at = datetime.now(timezone.utc)
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.updated_at = datetime.now(timezone.utc)

        mock_session.execute.return_value = mock_result_none

        async def mock_refresh(model):
            for attr in dir(mock_model):
                if not attr.startswith("_"):
                    try:
                        setattr(model, attr, getattr(mock_model, attr))
                    except AttributeError:
                        pass

        mock_session.refresh = mock_refresh

        # Execute
        result = await entity_memory_repo.create_or_update(sample_entity_memory_create)

        # Verify
        mock_session.add.assert_called_once()
        assert result.entity_id == 50
        assert result.summary == "OpenAI is an AI research company"

    @pytest.mark.asyncio
    async def test_create_or_update_update(
        self, entity_memory_repo, mock_session, sample_entity_memory_create
    ):
        """Test updating entity memory when it exists."""
        existing_model = MagicMock()
        existing_model.id = 1
        existing_model.entity_id = 50
        existing_model.summary = "Old summary"
        existing_model.related_topic_ids_json = [100]
        existing_model.milestones_json = []
        existing_model.recent_signals_json = []
        existing_model.last_refreshed_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        existing_model.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        existing_model.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await entity_memory_repo.create_or_update(sample_entity_memory_create)

        # Verify
        assert existing_model.summary == sample_entity_memory_create.summary
        assert existing_model.related_topic_ids_json == sample_entity_memory_create.related_topic_ids

    @pytest.mark.asyncio
    async def test_list_related_topics(self, entity_memory_repo, mock_session):
        """Test listing related topics for an entity."""
        mock_model = MagicMock()
        mock_model.topic_id = 100
        mock_model.relevance_score = 0.9

        mock_model2 = MagicMock()
        mock_model2.topic_id = 101
        mock_model2.relevance_score = 0.8

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model, mock_model2]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await entity_memory_repo.list_related_topics(50, limit=20)

        # Verify
        assert len(result) == 2
        assert 100 in result
        assert 101 in result

    @pytest.mark.asyncio
    async def test_attach_topic_entity(self, entity_memory_repo, mock_session):
        """Test attaching a topic to an entity."""
        # Execute
        await entity_memory_repo.attach_topic_entity(
            topic_id=100,
            entity_id=50,
            relevance_score=0.85,
        )

        # Verify
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_entities_for_topic(self, entity_memory_repo, mock_session):
        """Test listing entities for a topic."""
        mock_model = MagicMock()
        mock_model.entity_id = 50
        mock_model.relevance_score = 0.9

        mock_model2 = MagicMock()
        mock_model2.entity_id = 51
        mock_model2.relevance_score = 0.7

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model, mock_model2]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await entity_memory_repo.list_entities_for_topic(100, limit=20)

        # Verify
        assert len(result) == 2
        assert 50 in result
        assert 51 in result
