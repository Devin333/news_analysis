"""Tests for Topic Enrichment Pipeline."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.editorial.topic_enrichment_pipeline import (
    TopicEnrichmentPipeline,
    TopicEnrichmentResult,
)


@pytest.fixture
def mock_historian_service():
    """Create a mock historian service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_analyst_service():
    """Create a mock analyst service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_topic_memory_service():
    """Create a mock topic memory service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_insight_service():
    """Create a mock insight service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_timeline_service():
    """Create a mock timeline service."""
    service = AsyncMock()
    return service


@pytest.fixture
def enrichment_pipeline(
    mock_historian_service,
    mock_analyst_service,
    mock_topic_memory_service,
    mock_insight_service,
    mock_timeline_service,
):
    """Create an enrichment pipeline with mock services."""
    return TopicEnrichmentPipeline(
        historian_service=mock_historian_service,
        analyst_service=mock_analyst_service,
        topic_memory_service=mock_topic_memory_service,
        insight_service=mock_insight_service,
        timeline_service=mock_timeline_service,
    )


@pytest.fixture
def sample_historian_output():
    """Create a sample historian output."""
    output = MagicMock()
    output.historical_status = "new"
    output.history_summary = "Test history"
    output.first_seen_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    return output


@pytest.fixture
def sample_analyst_output():
    """Create a sample analyst output."""
    output = MagicMock()
    output.trend_stage = "emerging"
    output.system_judgement = "high_priority"
    output.why_it_matters = "Important development"
    return output


class TestTopicEnrichmentResult:
    """Tests for TopicEnrichmentResult."""

    def test_result_creation(self):
        """Test creating an enrichment result."""
        result = TopicEnrichmentResult(topic_id=100)

        assert result.topic_id == 100
        assert result.success is False
        assert result.historian_output is None
        assert result.analyst_output is None
        assert result.errors == []

    def test_result_with_outputs(self, sample_historian_output, sample_analyst_output):
        """Test result with outputs."""
        result = TopicEnrichmentResult(
            topic_id=100,
            success=True,
            historian_output=sample_historian_output,
            analyst_output=sample_analyst_output,
        )

        assert result.success is True
        assert result.historian_output is not None
        assert result.analyst_output is not None

    def test_result_to_dict(self, sample_historian_output, sample_analyst_output):
        """Test converting result to dict."""
        result = TopicEnrichmentResult(
            topic_id=100,
            success=True,
            historian_output=sample_historian_output,
            analyst_output=sample_analyst_output,
            metadata={"duration_ms": 1500},
        )

        result_dict = result.to_dict()

        assert result_dict["topic_id"] == 100
        assert result_dict["success"] is True
        assert result_dict["has_historian_output"] is True
        assert result_dict["has_analyst_output"] is True

    def test_result_with_errors(self):
        """Test result with errors."""
        result = TopicEnrichmentResult(
            topic_id=100,
            success=False,
            errors=["Historian failed", "Analyst failed"],
        )

        assert result.success is False
        assert len(result.errors) == 2


class TestTopicEnrichmentPipeline:
    """Tests for TopicEnrichmentPipeline."""

    @pytest.mark.asyncio
    async def test_enrich_topic_full_success(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_topic_memory_service,
        mock_insight_service,
        mock_timeline_service,
        sample_historian_output,
        sample_analyst_output,
    ):
        """Test full enrichment success."""
        # Setup mocks
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {"steps": 3})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {"steps": 2})
        )
        mock_topic_memory_service.update_from_historian = AsyncMock(return_value=True)
        mock_insight_service.update_from_analyst = AsyncMock(return_value=True)

        # Execute
        result = await enrichment_pipeline.enrich_topic(100)

        # Verify
        assert result.success is True
        assert result.historian_output is not None
        assert result.analyst_output is not None
        mock_timeline_service.refresh_topic_timeline.assert_called_once_with(100)
        mock_historian_service.run_for_topic.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_enrich_topic_historian_only(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_historian_output,
    ):
        """Test enrichment with historian only."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(
            100, run_analyst=False
        )

        # Verify
        assert result.success is True
        assert result.historian_output is not None
        assert result.analyst_output is None
        mock_analyst_service.run_for_topic.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_topic_analyst_only(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_analyst_output,
    ):
        """Test enrichment with analyst only."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(
            100, run_historian=False
        )

        # Verify
        assert result.success is True
        assert result.historian_output is None
        assert result.analyst_output is not None
        mock_historian_service.run_for_topic.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_topic_historian_failure(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_analyst_output,
    ):
        """Test enrichment when historian fails."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(None, {"error": "Failed"})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(100)

        # Verify
        assert result.success is False  # Historian failed
        assert result.historian_output is None
        assert "Historian" in result.errors[0]

    @pytest.mark.asyncio
    async def test_enrich_topic_analyst_failure(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_historian_output,
    ):
        """Test enrichment when analyst fails."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(None, {"error": "Failed"})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(100)

        # Verify
        assert result.success is False  # Analyst failed
        assert result.analyst_output is None
        assert "Analyst" in result.errors[0]

    @pytest.mark.asyncio
    async def test_enrich_topic_skip_timeline(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_historian_output,
        sample_analyst_output,
    ):
        """Test enrichment skipping timeline refresh."""
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(
            100, refresh_timeline=False
        )

        # Verify
        mock_timeline_service.refresh_topic_timeline.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_topic_no_save(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_topic_memory_service,
        mock_insight_service,
        mock_timeline_service,
        sample_historian_output,
        sample_analyst_output,
    ):
        """Test enrichment without saving results."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(
            100, save_results=False
        )

        # Verify
        assert result.success is True
        mock_topic_memory_service.update_from_historian.assert_not_called()
        mock_insight_service.update_from_analyst.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_topic_exception_handling(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_timeline_service,
    ):
        """Test enrichment handles exceptions gracefully."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(100)

        # Verify
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_enrich_topics_batch(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_historian_output,
        sample_analyst_output,
    ):
        """Test batch enrichment."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {})
        )

        # Execute
        results = await enrichment_pipeline.enrich_topics_batch([100, 101, 102])

        # Verify
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_enrich_topic_metadata(
        self,
        enrichment_pipeline,
        mock_historian_service,
        mock_analyst_service,
        mock_timeline_service,
        sample_historian_output,
        sample_analyst_output,
    ):
        """Test enrichment includes metadata."""
        mock_timeline_service.refresh_topic_timeline = AsyncMock()
        mock_historian_service.run_for_topic = AsyncMock(
            return_value=(sample_historian_output, {"steps": 3})
        )
        mock_analyst_service.run_for_topic = AsyncMock(
            return_value=(sample_analyst_output, {"steps": 2})
        )

        # Execute
        result = await enrichment_pipeline.enrich_topic(100)

        # Verify
        assert "started_at" in result.metadata
        assert "completed_at" in result.metadata
        assert "duration_ms" in result.metadata
