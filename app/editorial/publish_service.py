"""Publish Service for managing content publication.

Handles saving writer output and managing publication status.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.agents.writer.schemas import (
    CopyType,
    FeedCardCopyDTO,
    ReportSectionCopyDTO,
    TopicIntroCopyDTO,
    TrendCardCopyDTO,
    WriterOutput,
)
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.storage.repositories.topic_copy_repository import TopicCopyRepository
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class PublishService:
    """Service for managing content publication.

    Handles saving writer output, managing review status,
    and publishing approved content.
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

    async def save_writer_output(
        self,
        output: WriterOutput,
        *,
        auto_submit_for_review: bool = True,
    ) -> int | None:
        """Save writer output to database.

        Args:
            output: Writer output to save.
            auto_submit_for_review: Whether to auto-submit for review.

        Returns:
            Copy ID if saved, None otherwise.
        """
        if self._uow is None:
            logger.warning("UoW not available")
            return None

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            logger.warning("Topic copy repository not available")
            return None

        # Extract the actual copy content
        copy_content = output.get_copy()
        if copy_content is None:
            logger.warning("No copy content in writer output")
            return None

        # Convert to dict
        body = copy_content.model_dump()

        # Determine title
        title = self._extract_title(output)

        # Determine initial status
        status = "pending_review" if auto_submit_for_review else "draft"

        # Save to database
        model = await copy_repo.create(
            topic_id=output.topic_id,
            copy_type=output.copy_type.value,
            body=body,
            title=title,
            prompt_version=output.prompt_version,
            source_agent=output.source_agent,
            confidence=output.confidence,
            status=status,
            metadata=output.metadata,
        )

        logger.info(
            f"Saved {output.copy_type.value} copy for topic {output.topic_id} "
            f"with status {status}"
        )

        return model.id

    def _extract_title(self, output: WriterOutput) -> str | None:
        """Extract title from writer output.

        Args:
            output: Writer output.

        Returns:
            Title string or None.
        """
        copy = output.get_copy()
        if copy is None:
            return None

        if isinstance(copy, FeedCardCopyDTO):
            return copy.title
        elif isinstance(copy, TopicIntroCopyDTO):
            return copy.headline
        elif isinstance(copy, TrendCardCopyDTO):
            return copy.trend_title
        elif isinstance(copy, ReportSectionCopyDTO):
            return copy.section_title

        return None

    async def get_current_copy(
        self,
        topic_id: int,
        copy_type: CopyType,
        *,
        prefer_published: bool = True,
    ) -> dict[str, Any] | None:
        """Get the current effective copy for a topic.

        Args:
            topic_id: Topic ID.
            copy_type: Type of copy.
            prefer_published: Whether to prefer published over latest.

        Returns:
            Copy body dict or None.
        """
        if self._uow is None:
            return None

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return None

        if prefer_published:
            model = await copy_repo.get_published_by_topic_and_type(
                topic_id, copy_type.value
            )
            if model:
                return model.body_json

        # Fall back to latest
        model = await copy_repo.get_latest_by_topic_and_type(
            topic_id, copy_type.value
        )
        if model:
            return model.body_json

        return None

    async def publish_copy(self, copy_id: int) -> bool:
        """Publish a copy.

        Args:
            copy_id: Copy ID.

        Returns:
            True if published.
        """
        if self._uow is None:
            return False

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return False

        model = await copy_repo.publish(copy_id)
        if model:
            logger.info(f"Published copy {copy_id}")
            return True

        return False

    async def reject_copy(
        self,
        copy_id: int,
        *,
        reason: str | None = None,
    ) -> bool:
        """Reject a copy.

        Args:
            copy_id: Copy ID.
            reason: Rejection reason.

        Returns:
            True if rejected.
        """
        if self._uow is None:
            return False

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return False

        model = await copy_repo.update_status(
            copy_id,
            "rejected",
            review_status="rejected",
            review_notes=reason,
        )
        if model:
            logger.info(f"Rejected copy {copy_id}: {reason}")
            return True

        return False

    async def request_revision(
        self,
        copy_id: int,
        *,
        notes: str | None = None,
    ) -> bool:
        """Request revision for a copy.

        Args:
            copy_id: Copy ID.
            notes: Revision notes.

        Returns:
            True if updated.
        """
        if self._uow is None:
            return False

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return False

        model = await copy_repo.update_status(
            copy_id,
            "needs_revision",
            review_status="revise",
            review_notes=notes,
        )
        if model:
            logger.info(f"Requested revision for copy {copy_id}")
            return True

        return False

    async def approve_copy(
        self,
        copy_id: int,
        *,
        auto_publish: bool = False,
    ) -> bool:
        """Approve a copy.

        Args:
            copy_id: Copy ID.
            auto_publish: Whether to auto-publish after approval.

        Returns:
            True if approved.
        """
        if self._uow is None:
            return False

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return False

        status = "published" if auto_publish else "approved"
        model = await copy_repo.update_status(
            copy_id,
            status,
            review_status="approved",
        )
        if model:
            logger.info(f"Approved copy {copy_id} (auto_publish={auto_publish})")
            return True

        return False

    async def get_pending_reviews(
        self,
        *,
        copy_type: CopyType | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get copies pending review.

        Args:
            copy_type: Optional filter by type.
            limit: Maximum copies.

        Returns:
            List of copy dicts.
        """
        if self._uow is None:
            return []

        copy_repo = getattr(self._uow, "topic_copies", None)
        if copy_repo is None:
            return []

        type_str = copy_type.value if copy_type else None
        models = await copy_repo.list_pending_review(
            copy_type=type_str,
            limit=limit,
        )

        return [
            {
                "id": m.id,
                "topic_id": m.topic_id,
                "copy_type": m.copy_type,
                "title": m.title,
                "status": m.status,
                "confidence": m.confidence,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in models
        ]
