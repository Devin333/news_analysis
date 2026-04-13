"""Topic Copy Repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.topic_copy import TopicCopy

logger = get_logger(__name__)


class TopicCopyRepository:
    """Repository for topic copy operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        topic_id: int,
        copy_type: str,
        body: dict[str, Any],
        *,
        title: str | None = None,
        prompt_version: str = "v1",
        source_agent: str = "writer",
        confidence: float = 0.8,
        status: str = "draft",
        metadata: dict[str, Any] | None = None,
    ) -> TopicCopy:
        """Create a new topic copy.

        Args:
            topic_id: Topic ID.
            copy_type: Type of copy.
            body: Copy body as JSON.
            title: Optional title.
            prompt_version: Prompt version used.
            source_agent: Agent that generated the copy.
            confidence: Confidence score.
            status: Initial status.
            metadata: Additional metadata.

        Returns:
            Created TopicCopy.
        """
        model = TopicCopy(
            topic_id=topic_id,
            copy_type=copy_type,
            title=title,
            body_json=body,
            prompt_version=prompt_version,
            source_agent=source_agent,
            confidence=confidence,
            status=status,
            metadata_json=metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created {copy_type} copy for topic {topic_id}")
        return model

    async def get_by_id(self, copy_id: int) -> TopicCopy | None:
        """Get copy by ID.

        Args:
            copy_id: Copy ID.

        Returns:
            TopicCopy or None.
        """
        stmt = select(TopicCopy).where(TopicCopy.id == copy_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_topic_and_type(
        self,
        topic_id: int,
        copy_type: str,
    ) -> TopicCopy | None:
        """Get the latest copy for a topic and type.

        Args:
            topic_id: Topic ID.
            copy_type: Type of copy.

        Returns:
            Latest TopicCopy or None.
        """
        stmt = (
            select(TopicCopy)
            .where(
                TopicCopy.topic_id == topic_id,
                TopicCopy.copy_type == copy_type,
            )
            .order_by(TopicCopy.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_published_by_topic_and_type(
        self,
        topic_id: int,
        copy_type: str,
    ) -> TopicCopy | None:
        """Get the published copy for a topic and type.

        Args:
            topic_id: Topic ID.
            copy_type: Type of copy.

        Returns:
            Published TopicCopy or None.
        """
        stmt = (
            select(TopicCopy)
            .where(
                TopicCopy.topic_id == topic_id,
                TopicCopy.copy_type == copy_type,
                TopicCopy.status == "published",
            )
            .order_by(TopicCopy.published_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_topic(
        self,
        topic_id: int,
        *,
        copy_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[TopicCopy]:
        """List copies for a topic.

        Args:
            topic_id: Topic ID.
            copy_type: Optional filter by type.
            status: Optional filter by status.
            limit: Maximum copies to return.

        Returns:
            List of TopicCopy.
        """
        stmt = select(TopicCopy).where(TopicCopy.topic_id == topic_id)

        if copy_type:
            stmt = stmt.where(TopicCopy.copy_type == copy_type)
        if status:
            stmt = stmt.where(TopicCopy.status == status)

        stmt = stmt.order_by(TopicCopy.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_review(
        self,
        *,
        copy_type: str | None = None,
        limit: int = 50,
    ) -> list[TopicCopy]:
        """List copies pending review.

        Args:
            copy_type: Optional filter by type.
            limit: Maximum copies to return.

        Returns:
            List of TopicCopy pending review.
        """
        stmt = select(TopicCopy).where(TopicCopy.status == "pending_review")

        if copy_type:
            stmt = stmt.where(TopicCopy.copy_type == copy_type)

        stmt = stmt.order_by(TopicCopy.created_at.asc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        copy_id: int,
        status: str,
        *,
        review_status: str | None = None,
        review_notes: str | None = None,
    ) -> TopicCopy | None:
        """Update copy status.

        Args:
            copy_id: Copy ID.
            status: New status.
            review_status: Optional review status.
            review_notes: Optional review notes.

        Returns:
            Updated TopicCopy or None.
        """
        model = await self.get_by_id(copy_id)
        if model is None:
            return None

        model.status = status
        if review_status:
            model.review_status = review_status
        if review_notes:
            model.review_notes = review_notes
        if status in ("approved", "rejected"):
            model.reviewed_at = datetime.now(timezone.utc)
        if status == "published":
            model.published_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Updated copy {copy_id} status to {status}")
        return model

    async def publish(self, copy_id: int) -> TopicCopy | None:
        """Publish a copy.

        Args:
            copy_id: Copy ID.

        Returns:
            Published TopicCopy or None.
        """
        return await self.update_status(copy_id, "published")

    async def mark_for_review(self, copy_id: int) -> TopicCopy | None:
        """Mark a copy for review.

        Args:
            copy_id: Copy ID.

        Returns:
            Updated TopicCopy or None.
        """
        return await self.update_status(copy_id, "pending_review")

    async def delete(self, copy_id: int) -> bool:
        """Delete a copy.

        Args:
            copy_id: Copy ID.

        Returns:
            True if deleted.
        """
        model = await self.get_by_id(copy_id)
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()

        logger.info(f"Deleted copy {copy_id}")
        return True
