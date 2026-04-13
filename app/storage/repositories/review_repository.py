"""Review Repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.review_log import ReviewLog

logger = get_logger(__name__)


class ReviewRepository:
    """Repository for review log operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        target_type: str,
        target_id: int,
        review_status: str,
        *,
        copy_id: int | None = None,
        issues: list[dict[str, Any]] | None = None,
        missing_points: list[str] | None = None,
        unsupported_claims: list[str] | None = None,
        style_issues: list[str] | None = None,
        revision_hints: list[str] | None = None,
        review_summary: str | None = None,
        confidence: float = 0.8,
        source_agent: str = "reviewer",
        reviewer_version: str = "v1",
        metadata: dict[str, Any] | None = None,
    ) -> ReviewLog:
        """Create a review log.

        Args:
            target_type: Type of target (topic_copy, etc.).
            target_id: ID of the target.
            review_status: Review status.
            copy_id: Optional copy ID.
            issues: List of issues.
            missing_points: Missing points.
            unsupported_claims: Unsupported claims.
            style_issues: Style issues.
            revision_hints: Revision hints.
            review_summary: Review summary.
            confidence: Confidence score.
            source_agent: Agent that performed review.
            reviewer_version: Reviewer version.
            metadata: Additional metadata.

        Returns:
            Created ReviewLog.
        """
        model = ReviewLog(
            target_type=target_type,
            target_id=target_id,
            copy_id=copy_id,
            review_status=review_status,
            issues_json=issues or [],
            missing_points_json=missing_points or [],
            unsupported_claims_json=unsupported_claims or [],
            style_issues_json=style_issues or [],
            revision_hints_json=revision_hints or [],
            review_summary=review_summary,
            confidence=confidence,
            source_agent=source_agent,
            reviewer_version=reviewer_version,
            metadata_json=metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created review log for {target_type}:{target_id} with status {review_status}")
        return model

    async def get_by_id(self, review_id: int) -> ReviewLog | None:
        """Get review by ID.

        Args:
            review_id: Review ID.

        Returns:
            ReviewLog or None.
        """
        stmt = select(ReviewLog).where(ReviewLog.id == review_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_target(
        self,
        target_type: str,
        target_id: int,
        *,
        limit: int = 20,
    ) -> list[ReviewLog]:
        """List reviews for a target.

        Args:
            target_type: Type of target.
            target_id: ID of target.
            limit: Maximum reviews.

        Returns:
            List of ReviewLog.
        """
        stmt = (
            select(ReviewLog)
            .where(
                ReviewLog.target_type == target_type,
                ReviewLog.target_id == target_id,
            )
            .order_by(ReviewLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_copy(
        self,
        copy_id: int,
        *,
        limit: int = 10,
    ) -> list[ReviewLog]:
        """List reviews for a copy.

        Args:
            copy_id: Copy ID.
            limit: Maximum reviews.

        Returns:
            List of ReviewLog.
        """
        stmt = (
            select(ReviewLog)
            .where(ReviewLog.copy_id == copy_id)
            .order_by(ReviewLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_for_copy(self, copy_id: int) -> ReviewLog | None:
        """Get latest review for a copy.

        Args:
            copy_id: Copy ID.

        Returns:
            Latest ReviewLog or None.
        """
        stmt = (
            select(ReviewLog)
            .where(ReviewLog.copy_id == copy_id)
            .order_by(ReviewLog.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ReviewLog]:
        """List recent reviews.

        Args:
            status: Optional filter by status.
            limit: Maximum reviews.

        Returns:
            List of ReviewLog.
        """
        stmt = select(ReviewLog)

        if status:
            stmt = stmt.where(ReviewLog.review_status == status)

        stmt = stmt.order_by(ReviewLog.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
