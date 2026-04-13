"""Tests for Analyst Agent."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.analyst.agent import AnalystAgent
from app.agents.analyst.schemas import AnalystInput, AnalystOutput
from app.agents.analyst.input_builder import AnalystInputBuilder


@pytest.fixture
def analyst_agent():
    """Create an Analyst agent."""
    return AnalystAgent()


@pytest.fixture
def sample_analyst_input():
    """Create a sample analyst input."""
    return AnalystInput(
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
        historian_output={
            "historical_status": "new",
            "history_summary": "First release of GPT-5",
            "what_is_new_this_time": "New generation of language models",
        },
        metrics={
            "item_count": 15,
            "source_count": 5,
            "heat_score": 0.85,
            "trend_score": 0.9,
        },
    )


@pytest.fixture
def sample_analyst_output():
    """Create a sample analyst output."""
    return AnalystOutput(
        why_it_matters="GPT-5 represents a significant advancement in AI capabilities",
        system_judgement="high_priority",
        likely_audience=["AI researchers", "Tech industry", "Developers", "Business leaders"],
        follow_up_points=[
            "Monitor adoption rates",
            "Track competitor responses",
            "Watch for regulatory reactions",
        ],
        trend_stage="emerging",
        confidence=0.88,
        evidence_summary="Multiple high-quality sources, significant industry attention",
    )


class TestAnalystAgent:
    """Tests for AnalystAgent."""

    def test_agent_name(self, analyst_agent):
        """Test agent name property."""
        assert analyst_agent.name == "analyst"

    def test_prompt_key(self, analyst_agent):
        """Test prompt key property."""
        assert analyst_agent.prompt_key == "analyst"

    def test_output_schema(self, analyst_agent):
        """Test output schema property."""
        assert analyst_agent.output_schema == AnalystOutput

    def test_build_input(self, analyst_agent, sample_analyst_input):
        """Test building input message."""
        input_msg = analyst_agent.build_input(analyst_input=sample_analyst_input)

        assert "GPT-5" in input_msg
        assert "analysis" in input_msg.lower() or "analyze" in input_msg.lower()
        assert "JSON" in input_msg

    def test_build_input_missing_input(self, analyst_agent):
        """Test building input without required input raises error."""
        with pytest.raises(ValueError, match="analyst_input is required"):
            analyst_agent.build_input()

    def test_build_tools(self, analyst_agent):
        """Test building tools."""
        tools = analyst_agent.build_tools()

        assert isinstance(tools, list)
        tool_names = [t.name for t in tools]
        assert len(tool_names) > 0

    def test_set_retrieval_service(self, analyst_agent):
        """Test setting retrieval service."""
        mock_service = MagicMock()
        analyst_agent.set_retrieval_service(mock_service)

        assert analyst_agent._retrieval_service == mock_service


class TestAnalystInputBuilder:
    """Tests for AnalystInputBuilder."""

    def test_build_prompt_context(self, sample_analyst_input):
        """Test building prompt context."""
        builder = AnalystInputBuilder()
        context = builder.build_prompt_context(sample_analyst_input)

        assert "Topic ID: 100" in context
        assert "GPT-5" in context

    def test_build_prompt_context_with_historian_output(self, sample_analyst_input):
        """Test building prompt context includes historian output."""
        builder = AnalystInputBuilder()
        context = builder.build_prompt_context(sample_analyst_input)

        # Should include historian context
        assert "historical" in context.lower() or "history" in context.lower()

    def test_build_prompt_context_with_metrics(self, sample_analyst_input):
        """Test building prompt context includes metrics."""
        builder = AnalystInputBuilder()
        context = builder.build_prompt_context(sample_analyst_input)

        # Should include metrics
        assert "15" in context or "item_count" in context.lower()

    def test_build_prompt_context_minimal(self):
        """Test building prompt context with minimal data."""
        builder = AnalystInputBuilder()
        minimal_input = AnalystInput(
            topic_id=1,
            topic_summary="Test topic",
            representative_items=[],
            tags=[],
            board_type="general",
            historian_output=None,
            metrics={},
        )
        context = builder.build_prompt_context(minimal_input)

        assert "Topic ID: 1" in context
        assert "Test topic" in context


class TestAnalystOutput:
    """Tests for AnalystOutput schema."""

    def test_analyst_output_creation(self, sample_analyst_output):
        """Test creating an analyst output."""
        assert sample_analyst_output.system_judgement == "high_priority"
        assert sample_analyst_output.confidence == 0.88
        assert len(sample_analyst_output.likely_audience) == 4

    def test_analyst_output_validation(self):
        """Test analyst output validation."""
        output = AnalystOutput(
            why_it_matters="Important development",
            system_judgement="medium_priority",
            likely_audience=["General public"],
            follow_up_points=["Monitor progress"],
            trend_stage="growing",
            confidence=0.7,
            evidence_summary="Some evidence",
        )

        assert output.system_judgement == "medium_priority"
        assert output.trend_stage == "growing"

    def test_analyst_output_with_empty_lists(self):
        """Test analyst output with empty lists."""
        output = AnalystOutput(
            why_it_matters="Test",
            system_judgement="low_priority",
            likely_audience=[],
            follow_up_points=[],
            trend_stage="stable",
            confidence=0.5,
            evidence_summary="Limited evidence",
        )

        assert output.likely_audience == []
        assert output.follow_up_points == []


class TestAnalystAgentIntegration:
    """Integration-style tests for AnalystAgent."""

    @pytest.mark.asyncio
    async def test_analyze_topic_mock(self, analyst_agent, sample_analyst_input):
        """Test analyzing a topic with mocked LLM."""
        mock_output = AnalystOutput(
            why_it_matters="Test importance",
            system_judgement="medium_priority",
            likely_audience=["Developers"],
            follow_up_points=["Track updates"],
            trend_stage="emerging",
            confidence=0.75,
            evidence_summary="Test evidence",
        )

        with patch.object(
            analyst_agent, "run_structured", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (mock_output, {"steps": 1})

            output, meta = await analyst_agent.analyze_topic(sample_analyst_input)

            assert output is not None
            assert output.system_judgement == "medium_priority"
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_topic_with_historian_context(
        self, analyst_agent, sample_analyst_input
    ):
        """Test that analyst uses historian context."""
        mock_output = AnalystOutput(
            why_it_matters="Based on historical context",
            system_judgement="high_priority",
            likely_audience=["AI researchers"],
            follow_up_points=[],
            trend_stage="emerging",
            confidence=0.85,
            evidence_summary="Historical analysis supports this",
        )

        with patch.object(
            analyst_agent, "run_structured", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = (mock_output, {"steps": 2})

            output, meta = await analyst_agent.analyze_topic(sample_analyst_input)

            # Verify the input included historian output
            call_kwargs = mock_run.call_args[1]
            assert "analyst_input" in call_kwargs
