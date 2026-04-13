"""Topic Insight Repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.topic_insight import TopicInsight

logger = get_logger(__name__)


class TopicInsightDTO:
    """DTO for topic insight."""

    def __init__(
        self,
        id: int | None,
        topic_id: int,
        why_it_matters: str | None,
        system_judgement: str | None,
        likely_audience: list[str],
        follow_up_points: list[dict[str, Any]],
        trend_stage: str | None,
        trend_momentum: float | None,
        confidence: float | None,
        evidence_summary: str | None,
        key_signals: list[str],
        generated_at: datetime,
        source_agent: str,
        prompt_version: str | None,
    ) -> None:
        self.id = id
        self.topic_id = topic_id
        self.why_it_matters = why_it_matters
        self.system_judgement = system_judgement
        self.likely_audience = likely_audience
        self.follow_up_points = follow_up_points
        self.trend_stage = trend_stage
        self.trend_momentum = trend_momentum
        self.confidence = confidence
        self.evidence_summary = evidence_summary
        self.key_signals = key_signals
        self.generated_at = generated_at
        self.source_agent = source_agent
        self.prompt_version = prompt_version


class TopicInsightRepository:
    """Repository for topic insight operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        topic_id: int,
        why_it_matters: str | None,
        system_judgement: str | None,
        likely_audience: list[str],
        follow_up_points: list[dict[str, Any]],
        trend_stage: str | None,
        trend_momentum: float | None,
        confidence: float | None,
        evidence_summary: str | None = None,
        key_signals: list[str] | None = None,
        source_agent: str = "analyst",
        prompt_version: str | None = None,
    ) -> TopicInsightDTO:
        """Create a new topic insight.

        Args:
            topic_id: Topic ID.
            why_it_matters: Why the topic matters.
            system_judgement: System's judgement.
            likely_audience: List of audience types.
            follow_up_points: Points to follow up on.
            trend_stage: Current trend stage.
            trend_momentum: Trend momentum (-1 to 1).
            confidence: Confidence score (0-1).
            evidence_summary: Summary of evidence.
            key_signals: Key signals.
            source_agent: Agent that generated the insight.
            prompt_version: Version of prompt used.

        Returns:
            Created TopicInsightDTO.
        """
        now = datetime.now(timezone.utc)
        model = TopicInsight(
            topic_id=topic_id,
            why_it_matters=why_it_matters,
            system_judgement=system_judgement,
            likely_audience_json=likely_audience,
            follow_up_points_json=follow_up_points,
            trend_stage=trend_stage,
            trend_momentum=trend_momentum,
            confidence=confidence,
            evidence_summary=evidence_summary,
            key_signals_json=key_signals or [],
            generated_at=now,
            source_agent=source_agent,
            prompt_version=prompt_version,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created insight for topic {topic_id}")
        return self._to_dto(model)

    async def get_latest_by_topic_id(
        self,
        topic_id: int,
    ) -> TopicInsightDTO | None:
        """Get the latest insight for a topic.

        Args:
            topic_id: Topic ID.

        Returns:
            TopicInsightDTO if found, None otherwise.
        """
        stmt = (
            select(TopicInsight)
            .where(TopicInsight.topic_id == topic_id)
            .order_by(TopicInsight.generated_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dto(model)

    async def list_by_topic_id(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[TopicInsightDTO]:
        """List insights for a topic.

        Args:
            topic_id: Topic ID.
            limit: Maximum number of insights to return.

        Returns:
            List of TopicInsightDTO ordered by generated_at desc.
        """
        stmt = (
            select(TopicInsight)
            .where(TopicInsight.topic_id == topic_id)
            .order_by(TopicInsight.generated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_dto(m) for m in models]

    def _to_dto(self, model: TopicInsight) -> TopicInsightDTO:
        """Convert ORM model to DTO."""
        return TopicInsightDTO(
            id=model.id,
            topic_id=model.topic_id,
            why_it_matters=model.why_it_matters,
            system_judgement=model.system_judgement,
            likely_audience=model.likely_audience_json or [],
            follow_up_points=model.follow_up_points_json or [],
            trend_stage=model.trend_stage,
            trend_momentum=model.trend_momentum,
            confidence=model.confidence,
            evidence_summary=model.evidence_summary,
            key_signals=model.key_signals_json or [],
            generated_at=model.generated_at,
            source_agent=model.source_agent,
            prompt_version=model.prompt_version,
        )
