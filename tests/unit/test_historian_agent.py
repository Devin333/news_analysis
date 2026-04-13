"""Tests for Historian Agent."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.historian.agent import HistorianAgent
from app.agents.historian.schemas import HistorianInput, HistorianOutput, TimelinePoint
from app.agents.historian.input_builder import HistorianInputBuilder


@pytest.fixture
def historian_agent():
    """Create a Historian agent."""
    return HistorianAgent()


@pytest.fixture
def sample_historian_input():
    """Create a sample historian input."""
    return HistorianInput(
        topic_id=100,
        topic_summary="GPT-5 has been released by OpenAI",
        representative_items=[
            {
                "id": 1,
                "title": "OpenAI Releases GPT-5",
                "summary": "OpenAI announced the release of GPT-5",
                "published_at": "2024-01-15T10:00:00Z",
                "source_type": "news",
            }
        ],
        tags=["ai", "openai", "gpt", "llm"],
        board_type="tech",
        timeline=[
            {
                "event_time": "2024-01-15T10:00:00Z",
                "event_type": "first_seen",
                "title": "Topic First Appeared",
            }
        ],
        snapshots=[],
        related_topics=[],
        entity_memories=[],
    )


@pytest.fixture
def sample_historian_output():
    """Create a sample historian output."""
    return HistorianOutput(
        first_seen_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        history_summary="GPT-5 represents a major milestone in AI development",
        timeline_points=[
            TimelinePoint(
                event_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                event_type="first_seen",
                title="GPT-5 Announced",
                description="OpenAI officially announced GPT-5",
                importance_score=0.95,
            )
        ],
        historical_status="new",
        current_stage="emerging",
        what_is_new_this_time="First release of GPT-5, representing a new generation of language models",
        similar_past_topics=["GPT-4 release", "ChatGPT launch"],
        important_background="OpenAI has been developing GPT models since 2018",
        historical_confidence=0.85,
    )


class TestHistorianAgent:
    """Tests for HistorianAgent."""

    def test_agent_name(self, historian_agent):
        """Test agent name property."""
        assert historian_agent.name == "historian"

    def test_prompt_key(self, historian_agent):
        """Test prompt key property."""
        assert historian_agent.prompt_key == "historian"

    def test_output_schema(self, historian_agent):
        """Test output schema property."""
        assert historian_agent.output_schema == HistorianOutput

    def test_build_input(self, historian_agent, sample_historian_input):
        """Test building input message."""
        input_msg = historian_agent.build_input(historian_input=sample_historian_input)

        assert "GPT-5" in input_msg
        assert "historical" in input_msg.lower()
        assert "JSON" in input_msg

    def test_build_input_missing_input(self, historian_agent):
        """Test building input without required input raises error."""
        with pytest.raises(ValueError, match="historian_input is required"):
            historian_agent.build_input()

    def test_build_tools(self, historian_agent):
        """Test building tools."""
        tools = historian_agent.build_tools()

        assert isinstance(tools, list)
        # Should have history-related tools
        tool_names = [t.name for t in tools]
        assert len(tool_names) > 0

    def test_set_retrieval_service(self, historian_agent):
        """Test setting retrieval service."""
        mock_service = MagicMock()
        historian_agent.set_retrieval_service(mock_service)

        assert historian_agent._retrieval_service == mock_service


class TestHistorianInputBuilder:
    """Tests for HistorianInputBuilder."""

    def test_build_prompt_context(self, sample_historian_input):
        """Test building prompt context."""
        builder = HistorianInputBuilder()
        context = builder.build_prompt_context(sample_historian_input)

        assert "Topic ID: 100" in context
        assert "GPT-5" in context
        assert "ai" in context or "openai" in context

    def test_build_prompt_context_with_timeline(self, sample_historian_input):
        """Test building prompt context includes timeline."""
        builder = HistorianInputBuilder()
        context = builder.build_prompt_context(sample_historian_input)

        assert "Timeline" in context or "timeline" in context

    def test_build_prompt_context_with_empty_data(self):
        """Test building prompt context with minimal data."""
        builder = HistorianInputBuilder()
        minimal_input = HistorianInput(
            topic_id=1,
            topic_summary="Test topic",
            representative_items=[],
            tags=[],
            board_type="general",
            timeline=[],
            snapshots=[],
            related_topics=[],
            entity_memories=[],
        )
        context = builder.build_prompt_context(minimal_input)

        assert "Topic ID: 1" in context
        assert "Test topic" in context


class TestHistorianOutput:
    """Tests for HistorianOutput schema."""

    def test_historian_output_creation(self, sample_historian_output):
        """Test creating a historian output."""
        assert sample_historian_output.historical_status == "new"
        assert sample_historian_output.historical_confidence == 0.85
        assert len(sample_historian_output.timeline_points) == 1

    def test_historian_output_validation(self):
        """Test historian output validation."""
        output = HistorianOutput(
            first_seen_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            history_summary="Test summary",
            timeline_points=[],
            historical_status="evolving",
            current_stage="growing",
            what_is_new_this_time="New developments",
            similar_past_topics=[],
            important_background="Background info",
            historical_confidence=0.7,
        )

        assert output.historical_status == "evolving"
        assert output.current_stage == "growing"

    def test_timeline_point_creation(self):
        """Test creating a timeline point."""
        point = TimelinePoint(
            event_time=datetime(2024, 1, 15, tzinfo=timezone.utc),
            event_type="release_published",
            title="Major Release",
            description="A major release was published",
            importance_score=0.9,
        )

        assert point.event_type == "release_published"
        assert point.importance_score == 0.9


class TestHistorianAgentIntegration:
    """Integration-style tests for HistorianAgent."""

    @pytest.mark.asyncio
    async def test_analyze_topic_mock(self, historian_agent, sample_historian_input):
        """Test analyzing a topic with mocked LLM."""
        # Mock the run_structured method
        mock_output = HistorianOutput(
            first_seen_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            history_summary="Test summary",
            timeline_points=[],
            historical_status="new",
            current_stage="emerging",
            what_is_new_this_time="New topic",
            similar_past_topics=[],
            important_background="",
            historical_confidence=0.8,
        )

        with patch.object(
            historian_agent, "run_structured", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (mock_output, {"steps": 1})

            output, meta = await historian_agent.analyze_topic(sample_historian_input)

            assert output is not None
            assert output.historical_status == "new"
            mock_run.assert_called_once()
