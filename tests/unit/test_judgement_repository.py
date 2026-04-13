"""Tests for Judgement Repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.contracts.dto.memory import JudgementCreateDTO, JudgementMemoryDTO
from app.memory.repositories.judgement_repository import JudgementRepository


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
def judgement_repo(mock_session):
    """Create a judgement repository with mock session."""
    return JudgementRepository(mock_session)


@pytest.fixture
def sample_judgement_create():
    """Create a sample judgement create DTO."""
    return JudgementCreateDTO(
        target_type="topic",
        target_id=100,
        agent_name="analyst",
        judgement_type="importance",
        judgement="high_priority",
        confidence=0.85,
        evidence=["Multiple sources", "High engagement", "Expert mentions"],
        metadata={"prompt_version": "v1"},
    )


class TestJudgementRepository:
    """Tests for JudgementRepository."""

    @pytest.mark.asyncio
    async def test_create_log(
        self, judgement_repo, mock_session, sample_judgement_create
    ):
        """Test creating a judgement log."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.target_type = sample_judgement_create.target_type
        mock_model.target_id = sample_judgement_create.target_id
        mock_model.agent_name = sample_judgement_create.agent_name
        mock_model.judgement_type = sample_judgement_create.judgement_type
        mock_model.judgement = sample_judgement_create.judgement
        mock_model.confidence = sample_judgement_create.confidence
        mock_model.evidence_json = sample_judgement_create.evidence
        mock_model.metadata_json = sample_judgement_create.metadata
        mock_model.created_at = datetime.now(timezone.utc)
        mock_model.later_outcome = None

        async def mock_refresh(model):
            for attr in dir(mock_model):
                if not attr.startswith("_"):
                    try:
                        setattr(model, attr, getattr(mock_model, attr))
                    except AttributeError:
                        pass

        mock_session.refresh = mock_refresh

        # Execute
        result = await judgement_repo.create_log(sample_judgement_create)

        # Verify
        mock_session.add.assert_called_once()
        assert result.target_type == "topic"
        assert result.target_id == 100
        assert result.judgement == "high_priority"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_list_by_target(self, judgement_repo, mock_session):
        """Test listing judgements by target."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.target_type = "topic"
        mock_model.target_id = 100
        mock_model.agent_name = "analyst"
        mock_model.judgement_type = "importance"
        mock_model.judgement = "high_priority"
        mock_model.confidence = 0.85
        mock_model.evidence_json = ["Evidence 1"]
        mock_model.metadata_json = {}
        mock_model.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.later_outcome = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.list_by_target("topic", 100, limit=20)

        # Verify
        assert len(result) == 1
        assert result[0].target_type == "topic"
        assert result[0].target_id == 100
        assert result[0].judgement == "high_priority"

    @pytest.mark.asyncio
    async def test_list_recent_by_type(self, judgement_repo, mock_session):
        """Test listing recent judgements by type."""
        mock_model1 = MagicMock()
        mock_model1.id = 1
        mock_model1.target_type = "topic"
        mock_model1.target_id = 100
        mock_model1.agent_name = "analyst"
        mock_model1.judgement_type = "importance"
        mock_model1.judgement = "high_priority"
        mock_model1.confidence = 0.9
        mock_model1.evidence_json = []
        mock_model1.metadata_json = {}
        mock_model1.created_at = datetime(2024, 1, 20, tzinfo=timezone.utc)
        mock_model1.later_outcome = None

        mock_model2 = MagicMock()
        mock_model2.id = 2
        mock_model2.target_type = "topic"
        mock_model2.target_id = 101
        mock_model2.agent_name = "analyst"
        mock_model2.judgement_type = "importance"
        mock_model2.judgement = "medium_priority"
        mock_model2.confidence = 0.7
        mock_model2.evidence_json = []
        mock_model2.metadata_json = {}
        mock_model2.created_at = datetime(2024, 1, 19, tzinfo=timezone.utc)
        mock_model2.later_outcome = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model1, mock_model2]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.list_recent_by_type("importance", limit=20)

        # Verify
        assert len(result) == 2
        assert result[0].confidence == 0.9
        assert result[1].confidence == 0.7

    @pytest.mark.asyncio
    async def test_list_by_agent(self, judgement_repo, mock_session):
        """Test listing judgements by agent name."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.target_type = "topic"
        mock_model.target_id = 100
        mock_model.agent_name = "historian"
        mock_model.judgement_type = "historical_status"
        mock_model.judgement = "evolving"
        mock_model.confidence = 0.8
        mock_model.evidence_json = ["Timeline analysis"]
        mock_model.metadata_json = {}
        mock_model.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.later_outcome = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.list_by_agent("historian", limit=20)

        # Verify
        assert len(result) == 1
        assert result[0].agent_name == "historian"
        assert result[0].judgement_type == "historical_status"

    @pytest.mark.asyncio
    async def test_update_outcome(self, judgement_repo, mock_session):
        """Test updating the later outcome of a judgement."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.target_type = "topic"
        mock_model.target_id = 100
        mock_model.agent_name = "analyst"
        mock_model.judgement_type = "trend_prediction"
        mock_model.judgement = "will_grow"
        mock_model.confidence = 0.75
        mock_model.evidence_json = []
        mock_model.metadata_json = {}
        mock_model.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.later_outcome = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.update_outcome(1, "confirmed_growth")

        # Verify
        assert mock_model.later_outcome == "confirmed_growth"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_outcome_not_found(self, judgement_repo, mock_session):
        """Test updating outcome when judgement not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.update_outcome(999, "some_outcome")

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_find_similar_judgements(self, judgement_repo, mock_session):
        """Test finding similar judgements (stub implementation)."""
        # This is a stub test - the actual implementation may use embeddings
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.find_similar_judgements(
            judgement_text="high_priority",
            limit=10,
        )

        # Verify - stub returns empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_id(self, judgement_repo, mock_session):
        """Test getting a judgement by ID."""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.target_type = "topic"
        mock_model.target_id = 100
        mock_model.agent_name = "analyst"
        mock_model.judgement_type = "importance"
        mock_model.judgement = "high_priority"
        mock_model.confidence = 0.85
        mock_model.evidence_json = ["Evidence"]
        mock_model.metadata_json = {}
        mock_model.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
        mock_model.later_outcome = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.get_by_id(1)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.judgement == "high_priority"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, judgement_repo, mock_session):
        """Test getting a judgement by ID when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await judgement_repo.get_by_id(999)

        # Verify
        assert result is None
