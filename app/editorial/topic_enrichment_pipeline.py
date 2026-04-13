"""Topic Enrichment Pipeline.

Orchestrates the full enrichment workflow for topics:
1. Refresh timeline
2. Run Historian
3. Save topic memory
4. Run Analyst
5. Save insight
6. Refresh topic detail model
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agents.analyst.schemas import AnalystOutput
    from app.agents.analyst.service import AnalystService
    from app.agents.historian.schemas import HistorianOutput
    from app.agents.historian.service import HistorianService
    from app.editorial.insight_service import InsightService
    from app.memory.timeline.service import TimelineService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class TopicEnrichmentResult:
    """Result of topic enrichment."""

    def __init__(
        self,
        topic_id: int,
        success: bool = False,
        historian_output: "HistorianOutput | None" = None,
        analyst_output: "AnalystOutput | None" = None,
        errors: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.topic_id = topic_id
        self.success = success
        self.historian_output = historian_output
        self.analyst_output = analyst_output
        self.errors = errors or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic_id": self.topic_id,
            "success": self.success,
            "has_historian_output": self.historian_output is not None,
            "has_analyst_output": self.analyst_output is not None,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class TopicEnrichmentPipeline:
    """Pipeline for enriching topics with historical context and insights."""

    def __init__(
        self,
        historian_service: "HistorianService | None" = None,
        analyst_service: "AnalystService | None" = None,
        topic_memory_service: "TopicMemoryService | None" = None,
        insight_service: "InsightService | None" = None,
        timeline_service: "TimelineService | None" = None,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            historian_service: Service for running Historian.
            analyst_service: Service for running Analyst.
            topic_memory_service: Service for topic memory persistence.
            insight_service: Service for insight persistence.
            timeline_service: Service for timeline operations.
            uow: Unit of work for database access.
        """
        self._historian_service = historian_service
        self._analyst_service = analyst_service
        self._topic_memory_service = topic_memory_service
        self._insight_service = insight_service
        self._timeline_service = timeline_service
        self._uow = uow

    async def enrich_topic(
        self,
        topic_id: int,
        *,
        run_historian: bool = True,
        run_analyst: bool = True,
        refresh_timeline: bool = True,
        save_results: bool = True,
    ) -> TopicEnrichmentResult:
        """Run full enrichment pipeline for a topic.

        Args:
            topic_id: ID of the topic to enrich.
            run_historian: Whether to run Historian.
            run_analyst: Whether to run Analyst.
            refresh_timeline: Whether to refresh timeline first.
            save_results: Whether to save results to database.

        Returns:
            TopicEnrichmentResult with outputs and metadata.
        """
        start_time = datetime.utcnow()
        result = TopicEnrichmentResult(topic_id=topic_id)
        result.metadata["started_at"] = start_time.isoformat()

        try:
            # Step 1: Refresh timeline
            if refresh_timeline and self._timeline_service:
                logger.info(f"Refreshing timeline for topic {topic_id}")
                try:
                    await self._timeline_service.refresh_topic_timeline(topic_id)
                    result.metadata["timeline_refreshed"] = True
                except Exception as e:
                    logger.warning(f"Timeline refresh failed: {e}")
                    result.errors.append(f"Timeline refresh failed: {e}")

            # Step 2: Run Historian
            historian_output = None
            if run_historian and self._historian_service:
                logger.info(f"Running Historian for topic {topic_id}")
                historian_output, historian_meta = await self._historian_service.run_for_topic(
                    topic_id
                )
                result.metadata["historian"] = historian_meta

                if historian_output:
                    result.historian_output = historian_output
                    logger.info(
                        f"Historian completed: status={historian_output.historical_status}"
                    )

                    # Step 3: Save topic memory
                    if save_results and self._topic_memory_service:
                        saved = await self._topic_memory_service.update_from_historian(
                            topic_id, historian_output
                        )
                        result.metadata["historian_saved"] = saved
                else:
                    result.errors.append("Historian analysis failed")

            # Step 4: Run Analyst
            analyst_output = None
            if run_analyst and self._analyst_service:
                logger.info(f"Running Analyst for topic {topic_id}")
                analyst_output, analyst_meta = await self._analyst_service.run_for_topic(
                    topic_id,
                    historian_output=historian_output,
                )
                result.metadata["analyst"] = analyst_meta

                if analyst_output:
                    result.analyst_output = analyst_output
                    logger.info(
                        f"Analyst completed: trend={analyst_output.trend_stage}"
                    )

                    # Step 5: Save insight
                    if save_results and self._insight_service:
                        saved = await self._insight_service.update_from_analyst(
                            topic_id, analyst_output
                        )
                        result.metadata["insight_saved"] = saved
                else:
                    result.errors.append("Analyst analysis failed")

            # Determine overall success
            result.success = (
                (not run_historian or historian_output is not None) and
                (not run_analyst or analyst_output is not None)
            )

        except Exception as e:
            logger.error(f"Enrichment pipeline failed for topic {topic_id}: {e}")
            result.errors.append(str(e))
            result.success = False

        # Finalize metadata
        end_time = datetime.utcnow()
        result.metadata["completed_at"] = end_time.isoformat()
        result.metadata["duration_ms"] = (end_time - start_time).total_seconds() * 1000

        logger.info(
            f"Enrichment {'completed' if result.success else 'failed'} for topic {topic_id} "
            f"in {result.metadata['duration_ms']:.1f}ms"
        )

        return result

    async def enrich_topics_batch(
        self,
        topic_ids: list[int],
        **kwargs,
    ) -> list[TopicEnrichmentResult]:
        """Enrich multiple topics.

        Args:
            topic_ids: List of topic IDs to enrich.
            **kwargs: Arguments passed to enrich_topic.

        Returns:
            List of TopicEnrichmentResult.
        """
        results = []
        for topic_id in topic_ids:
            result = await self.enrich_topic(topic_id, **kwargs)
            results.append(result)
        return results


async def create_enrichment_pipeline(
    uow: "UnitOfWork | None" = None,
) -> TopicEnrichmentPipeline:
    """Create a fully configured enrichment pipeline.

    Args:
        uow: Unit of work for database access.

    Returns:
        Configured TopicEnrichmentPipeline.
    """
    from app.agents.analyst.service import AnalystService
    from app.agents.historian.service import HistorianService
    from app.editorial.insight_service import InsightService
    from app.memory.retrieval.service import MemoryRetrievalService
    from app.memory.timeline.service import TimelineService
    from app.memory.topic_memory.service import TopicMemoryService
    from app.storage.uow import UnitOfWork

    if uow is None:
        uow = UnitOfWork()

    # Create services
    topic_memory_service = TopicMemoryService(uow=uow)
    insight_service = InsightService(uow=uow)
    timeline_service = TimelineService(uow=uow)

    # Create retrieval service (simplified - would need proper initialization)
    retrieval_service = None  # MemoryRetrievalService(...)

    historian_service = HistorianService(
        retrieval_service=retrieval_service,
        uow=uow,
    )
    analyst_service = AnalystService(
        retrieval_service=retrieval_service,
        uow=uow,
    )

    return TopicEnrichmentPipeline(
        historian_service=historian_service,
        analyst_service=analyst_service,
        topic_memory_service=topic_memory_service,
        insight_service=insight_service,
        timeline_service=timeline_service,
        uow=uow,
    )
