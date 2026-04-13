"""Ranking tracing for debugging and analysis.

Provides logging and tracing for ranking computations.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.ranking import (
    RankedTopicDTO,
    RankingContextDTO,
    RankingFeatureDTO,
    RankingScoreDTO,
)
from app.storage.db.models.ranking_log import RankingLog

logger = get_logger(__name__)


class RankingTracer:
    """Tracer for ranking computations.

    Records ranking decisions for debugging and analysis.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize tracer.

        Args:
            session: Database session for persistence.
            enabled: Whether tracing is enabled.
        """
        self._session = session
        self._enabled = enabled
        self._in_memory_logs: list[dict[str, Any]] = []

    async def trace_score(
        self,
        topic_id: int,
        features: RankingFeatureDTO,
        score: RankingScoreDTO,
        context: RankingContextDTO,
        *,
        rank_position: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Trace a single topic score computation.

        Args:
            topic_id: Topic ID.
            features: Computed features.
            score: Computed score.
            context: Ranking context.
            rank_position: Position in ranked list.
            batch_size: Total items in batch.
        """
        if not self._enabled:
            return

        log_entry = {
            "target_type": "topic",
            "target_id": topic_id,
            "ranking_context": context.context_name,
            "strategy_name": score.strategy_name,
            "features_json": features.model_dump(),
            "final_score": score.final_score,
            "component_scores_json": score.component_scores,
            "explanation": score.explanation,
            "top_factors_json": score.top_factors,
            "rank_position": rank_position,
            "batch_size": batch_size,
            "request_id": context.request_id,
            "user_key": context.user_key,
            "created_at": datetime.now(timezone.utc),
        }

        # Store in memory
        self._in_memory_logs.append(log_entry)

        # Persist if session available
        if self._session:
            await self._persist_log(log_entry)

        logger.debug(
            f"Traced ranking: topic={topic_id}, context={context.context_name}, "
            f"score={score.final_score:.3f}, rank={rank_position}"
        )

    async def trace_batch(
        self,
        ranked_topics: list[RankedTopicDTO],
        context: RankingContextDTO,
    ) -> None:
        """Trace a batch ranking operation.

        Args:
            ranked_topics: List of ranked topics.
            context: Ranking context.
        """
        if not self._enabled:
            return

        batch_size = len(ranked_topics)

        for topic in ranked_topics:
            if topic.features:
                score = RankingScoreDTO(
                    topic_id=topic.topic_id,
                    final_score=topic.score,
                    strategy_name=topic.strategy_name,
                    component_scores=topic.score_breakdown,
                    context_name=context.context_name,
                )
                await self.trace_score(
                    topic.topic_id,
                    topic.features,
                    score,
                    context,
                    rank_position=topic.rank,
                    batch_size=batch_size,
                )

    async def _persist_log(self, log_entry: dict[str, Any]) -> None:
        """Persist log entry to database.

        Args:
            log_entry: Log entry dict.
        """
        if not self._session:
            return

        try:
            model = RankingLog(
                target_type=log_entry["target_type"],
                target_id=log_entry["target_id"],
                ranking_context=log_entry["ranking_context"],
                strategy_name=log_entry["strategy_name"],
                features_json=log_entry["features_json"],
                final_score=log_entry["final_score"],
                component_scores_json=log_entry["component_scores_json"],
                explanation=log_entry.get("explanation"),
                top_factors_json=log_entry.get("top_factors_json", []),
                rank_position=log_entry.get("rank_position"),
                batch_size=log_entry.get("batch_size"),
                request_id=log_entry.get("request_id"),
                user_key=log_entry.get("user_key"),
            )
            self._session.add(model)
            await self._session.flush()
        except Exception as e:
            logger.warning(f"Failed to persist ranking log: {e}")

    def get_recent_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent in-memory logs.

        Args:
            limit: Maximum logs to return.

        Returns:
            List of log entries.
        """
        return self._in_memory_logs[-limit:]

    def get_logs_for_topic(self, topic_id: int) -> list[dict[str, Any]]:
        """Get logs for a specific topic.

        Args:
            topic_id: Topic ID.

        Returns:
            List of log entries for the topic.
        """
        return [
            log for log in self._in_memory_logs
            if log["target_id"] == topic_id
        ]

    def get_logs_for_context(self, context_name: str) -> list[dict[str, Any]]:
        """Get logs for a specific context.

        Args:
            context_name: Context name.

        Returns:
            List of log entries for the context.
        """
        return [
            log for log in self._in_memory_logs
            if log["ranking_context"] == context_name
        ]

    def clear_memory_logs(self) -> None:
        """Clear in-memory logs."""
        self._in_memory_logs.clear()

    def disable(self) -> None:
        """Disable tracing."""
        self._enabled = False

    def enable(self) -> None:
        """Enable tracing."""
        self._enabled = True


class RankingLogRepository:
    """Repository for ranking log queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Database session.
        """
        self._session = session

    async def get_by_id(self, log_id: int) -> RankingLog | None:
        """Get log by ID.

        Args:
            log_id: Log ID.

        Returns:
            RankingLog or None.
        """
        from sqlalchemy import select

        stmt = select(RankingLog).where(RankingLog.id == log_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_topic(
        self,
        topic_id: int,
        *,
        limit: int = 50,
    ) -> list[RankingLog]:
        """List logs for a topic.

        Args:
            topic_id: Topic ID.
            limit: Maximum logs.

        Returns:
            List of RankingLog.
        """
        from sqlalchemy import select

        stmt = (
            select(RankingLog)
            .where(
                RankingLog.target_type == "topic",
                RankingLog.target_id == topic_id,
            )
            .order_by(RankingLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_context(
        self,
        context_name: str,
        *,
        limit: int = 100,
    ) -> list[RankingLog]:
        """List logs for a context.

        Args:
            context_name: Context name.
            limit: Maximum logs.

        Returns:
            List of RankingLog.
        """
        from sqlalchemy import select

        stmt = (
            select(RankingLog)
            .where(RankingLog.ranking_context == context_name)
            .order_by(RankingLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_recent(
        self,
        *,
        limit: int = 100,
    ) -> list[RankingLog]:
        """List recent logs.

        Args:
            limit: Maximum logs.

        Returns:
            List of RankingLog.
        """
        from sqlalchemy import select

        stmt = (
            select(RankingLog)
            .order_by(RankingLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_topic_ranking_history(
        self,
        topic_id: int,
        context_name: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get ranking history for a topic in a context.

        Args:
            topic_id: Topic ID.
            context_name: Context name.
            limit: Maximum entries.

        Returns:
            List of ranking history entries.
        """
        logs = await self.list_by_topic(topic_id, limit=limit)
        return [
            {
                "id": log.id,
                "context": log.ranking_context,
                "strategy": log.strategy_name,
                "score": log.final_score,
                "rank": log.rank_position,
                "top_factors": log.top_factors_json,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
            if log.ranking_context == context_name
        ]
