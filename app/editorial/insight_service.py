"""Insight Service.

Handles persistence and retrieval of analyst insights.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agents.analyst.schemas import AnalystOutput
    from app.storage.repositories.topic_insight_repository import (
        TopicInsightDTO,
        TopicInsightRepository,
    )
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class InsightService:
    """Service for managing topic insights.

    Coordinates:
    - Saving analyst output
    - Retrieving insights
    - Building insight views
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
        """
        self._uow = uow

    async def save_analyst_output(
        self,
        topic_id: int,
        output: "AnalystOutput",
        prompt_version: str = "v1",
    ) -> bool:
        """Save analyst output as topic insight.

        Args:
            topic_id: ID of the topic.
            output: Analyst output to save.
            prompt_version: Version of prompt used.

        Returns:
            True if saved successfully.
        """
        if self._uow is None:
            logger.warning("No UoW available, cannot save analyst output")
            return False

        try:
            from app.storage.repositories.topic_insight_repository import (
                TopicInsightRepository,
            )

            async with self._uow:
                # Create repository
                repo = TopicInsightRepository(self._uow.session)

                # Convert follow-up points to dicts
                follow_up_points = [
                    {
                        "topic": fp.topic,
                        "reason": fp.reason,
                        "priority": fp.priority,
                    }
                    for fp in output.follow_up_points
                ]

                # Create insight
                await repo.create(
                    topic_id=topic_id,
                    why_it_matters=output.why_it_matters,
                    system_judgement=output.system_judgement,
                    likely_audience=output.likely_audience,
                    follow_up_points=follow_up_points,
                    trend_stage=output.trend_stage.value,
                    trend_momentum=output.trend_momentum,
                    confidence=output.confidence,
                    evidence_summary=output.evidence_summary,
                    key_signals=output.key_signals,
                    source_agent="analyst",
                    prompt_version=prompt_version,
                )

                await self._uow.commit()
                logger.info(f"Saved analyst insight for topic {topic_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving analyst output for topic {topic_id}: {e}")
            return False

    async def get_latest_insight(
        self,
        topic_id: int,
    ) -> "TopicInsightDTO | None":
        """Get the latest insight for a topic.

        Args:
            topic_id: ID of the topic.

        Returns:
            TopicInsightDTO or None.
        """
        if self._uow is None:
            return None

        try:
            from app.storage.repositories.topic_insight_repository import (
                TopicInsightRepository,
            )

            async with self._uow:
                repo = TopicInsightRepository(self._uow.session)
                return await repo.get_latest_by_topic_id(topic_id)

        except Exception as e:
            logger.error(f"Error getting insight for topic {topic_id}: {e}")
            return None

    async def get_insight_dict(
        self,
        topic_id: int,
    ) -> dict[str, Any] | None:
        """Get insight as dictionary for API response.

        Args:
            topic_id: ID of the topic.

        Returns:
            Insight dict or None.
        """
        insight = await self.get_latest_insight(topic_id)
        if insight is None:
            return None

        return {
            "topic_id": insight.topic_id,
            "why_it_matters": insight.why_it_matters,
            "system_judgement": insight.system_judgement,
            "likely_audience": insight.likely_audience,
            "follow_up_points": insight.follow_up_points,
            "trend_stage": insight.trend_stage,
            "trend_momentum": insight.trend_momentum,
            "confidence": insight.confidence,
            "evidence_summary": insight.evidence_summary,
            "key_signals": insight.key_signals,
            "generated_at": insight.generated_at.isoformat(),
        }

    async def update_from_analyst(
        self,
        topic_id: int,
        output: "AnalystOutput",
    ) -> bool:
        """Update topic insight from analyst output.

        This is the main entry point for persisting analyst results.

        Args:
            topic_id: ID of the topic.
            output: Analyst output.

        Returns:
            True if updated successfully.
        """
        # Save the analyst output
        saved = await self.save_analyst_output(topic_id, output)

        if saved:
            # Create a judgement log
            await self._create_analyst_judgement(topic_id, output)

        return saved

    async def _create_analyst_judgement(
        self,
        topic_id: int,
        output: "AnalystOutput",
    ) -> None:
        """Create a judgement log entry for analyst analysis.

        Args:
            topic_id: ID of the topic.
            output: Analyst output.
        """
        if self._uow is None:
            return

        try:
            from app.contracts.dto.memory import JudgementCreateDTO

            async with self._uow:
                # Build evidence list
                evidence = []
                if output.why_it_matters:
                    evidence.append(f"Why: {output.why_it_matters[:150]}")
                evidence.append(f"Trend: {output.trend_stage.value}")
                evidence.append(f"Audience: {', '.join(output.likely_audience[:3])}")

                judgement_dto = JudgementCreateDTO(
                    target_type="topic",
                    target_id=topic_id,
                    agent_name="analyst",
                    judgement_type="value_analysis",
                    judgement=output.system_judgement or "No judgement",
                    confidence=output.confidence,
                    evidence=evidence,
                )
                await self._uow.judgements.create_log(judgement_dto)
                await self._uow.commit()
                logger.debug(f"Created analyst judgement for topic {topic_id}")

        except Exception as e:
            logger.warning(f"Failed to create analyst judgement: {e}")
