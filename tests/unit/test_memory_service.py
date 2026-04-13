"""Unit tests for Memory repositories and service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.dto.memory import (
    EntityMemoryCreateDTO,
    EntityMemoryDTO,
    JudgementCreateDTO,
    JudgementMemoryDTO,
    TopicMemoryCreateDTO,
    TopicMemoryDTO,
    TopicSnapshotCreateDTO,
    TopicSnapshotDTO,
)
from app.memory.service import MemoryService


class TestMemoryService:
    """Tests for MemoryService."""

    @pytest.fixture
    def mock_topic_memory_repo(self):
        """Create mock topic memory repository."""
        repo = MagicMock()
        repo.get_by_topic_id = AsyncMock(return_value=None)
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.create_snapshot = AsyncMock()
        repo.list_snapshots = AsyncMock(return_value=[])
        repo.get_latest_snapshot = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_entity_memory_repo(self):
        """Create mock entity memory repository."""
        repo = MagicMock()
        repo.get_by_entity_id = AsyncMock(return_value=None)
        repo.create_or_update = AsyncMock()
        repo.list_related_topics = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_judgement_repo(self):
        """Create mock judgement repository."""
        repo = MagicMock()
        repo.create_log = AsyncMock()
        repo.list_by_target = AsyncMock(return_value=[])
        repo.list_recent_by_type = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def memory_service(
        self,
        mock_topic_memory_repo,
        mock_entity_memory_repo,
        mock_judgement_repo,
    ):
        """Create memory service with mocks."""
        return MemoryService(
            topic_memory_repo=mock_topic_memory_repo,
            entity_memory_repo=mock_entity_memory_repo,
            judgement_repo=mock_judgement_repo,
        )

    @pytest.mark.asyncio
    async def test_get_topic_memory_not_found(
        self,
        memory_service,
        mock_topic_memory_repo,
    ):
        """Test getting non-existent topic memory."""
        mock_topic_memory_repo.get_by_topic_id.return_value = None

        result = await memory_service.get_topic_memory(123)

        assert result is None
        mock_topic_memory_repo.get_by_topic_id.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_topic_memory_found(
        self,
        memory_service,
        mock_topic_memory_repo,
    ):
        """Test getting existing topic memory."""
        now = datetime.now(timezone.utc)
        expected = TopicMemoryDTO(
            id=1,
            topic_id=123,
            first_seen_at=now,
            last_seen_at=now,
            historical_status="new",
            current_stage="emerging",
        )
        mock_topic_memory_repo.get_by_topic_id.return_value = expected

        result = await memory_service.get_topic_memory(123)

        assert result == expected
        assert result.topic_id == 123

    @pytest.mark.asyncio
    async def test_create_topic_memory(
        self,
        memory_service,
        mock_topic_memory_repo,
    ):
        """Test creating topic memory."""
        now = datetime.now(timezone.utc)
        create_dto = TopicMemoryCreateDTO(
            topic_id=123,
            first_seen_at=now,
            historical_status="new",
            current_stage="emerging",
        )
        expected = TopicMemoryDTO(
            id=1,
            topic_id=123,
            first_seen_at=now,
            last_seen_at=now,
            historical_status="new",
            current_stage="emerging",
        )
        mock_topic_memory_repo.get_by_topic_id.return_value = None
        mock_topic_memory_repo.create.return_value = expected

        result = await memory_service.create_or_update_topic_memory(123, create_dto)

        assert result == expected
        mock_topic_memory_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_topic_snapshot(
        self,
        memory_service,
        mock_topic_memory_repo,
    ):
        """Test creating topic snapshot."""
        now = datetime.now(timezone.utc)
        snapshot_data = TopicSnapshotCreateDTO(
            topic_id=123,
            summary="Test summary",
            heat_score=50.0,
            item_count=10,
        )
        expected = TopicSnapshotDTO(
            id=1,
            topic_id=123,
            snapshot_at=now,
            summary="Test summary",
            heat_score=50.0,
            item_count=10,
        )
        mock_topic_memory_repo.create_snapshot.return_value = expected

        result = await memory_service.create_topic_snapshot(123, snapshot_data)

        assert result == expected
        assert result.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_get_topic_snapshots(
        self,
        memory_service,
        mock_topic_memory_repo,
    ):
        """Test getting topic snapshots."""
        now = datetime.now(timezone.utc)
        snapshots = [
            TopicSnapshotDTO(id=1, topic_id=123, snapshot_at=now, heat_score=50.0),
            TopicSnapshotDTO(id=2, topic_id=123, snapshot_at=now, heat_score=60.0),
        ]
        mock_topic_memory_repo.list_snapshots.return_value = snapshots

        result = await memory_service.get_topic_snapshots(123, limit=10)

        assert len(result) == 2
        mock_topic_memory_repo.list_snapshots.assert_called_once_with(123, 10)

    @pytest.mark.asyncio
    async def test_create_judgement_log(
        self,
        memory_service,
        mock_judgement_repo,
    ):
        """Test creating judgement log."""
        now = datetime.now(timezone.utc)
        create_dto = JudgementCreateDTO(
            target_type="topic",
            target_id=123,
            agent_name="analyst",
            judgement_type="importance",
            judgement="High importance",
            confidence=0.9,
        )
        expected = JudgementMemoryDTO(
            id=1,
            target_type="topic",
            target_id=123,
            agent_name="analyst",
            judgement_type="importance",
            judgement="High importance",
            confidence=0.9,
            created_at=now,
        )
        mock_judgement_repo.create_log.return_value = expected

        result = await memory_service.create_judgement_log(create_dto)

        assert result == expected
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_get_judgements_for_target(
        self,
        memory_service,
        mock_judgement_repo,
    ):
        """Test getting judgements for target."""
        now = datetime.now(timezone.utc)
        judgements = [
            JudgementMemoryDTO(
                id=1,
                target_type="topic",
                target_id=123,
                agent_name="analyst",
                judgement_type="importance",
                judgement="High",
                confidence=0.9,
                created_at=now,
            ),
        ]
        mock_judgement_repo.list_by_target.return_value = judgements

        result = await memory_service.get_judgements_for_target("topic", 123)

        assert len(result) == 1
        mock_judgement_repo.list_by_target.assert_called_once_with("topic", 123, 20)

    @pytest.mark.asyncio
    async def test_retrieve_topic_context(
        self,
        memory_service,
        mock_topic_memory_repo,
        mock_judgement_repo,
    ):
        """Test retrieving topic context."""
        now = datetime.now(timezone.utc)
        topic_memory = TopicMemoryDTO(
            id=1,
            topic_id=123,
            first_seen_at=now,
            last_seen_at=now,
            historical_status="evolving",
            current_stage="active",
        )
        mock_topic_memory_repo.get_by_topic_id.return_value = topic_memory
        mock_topic_memory_repo.get_latest_snapshot.return_value = None
        mock_judgement_repo.list_by_target.return_value = []

        result = await memory_service.retrieve_topic_context(123)

        assert result.topic_id == 123
        assert result.topic_memory == topic_memory
        assert result.latest_snapshot is None

    @pytest.mark.asyncio
    async def test_service_without_repos(self):
        """Test service behavior without repositories."""
        service = MemoryService()

        # Should return None/empty without errors
        assert await service.get_topic_memory(123) is None
        assert await service.get_topic_snapshots(123) == []
        assert await service.get_entity_memory(456) is None
        assert await service.get_judgements_for_target("topic", 123) == []
