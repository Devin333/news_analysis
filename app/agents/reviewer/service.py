"""Reviewer Agent service.

Provides high-level methods for reviewing different types of content.
"""

from typing import TYPE_CHECKING, Any

from app.agents.reviewer.agent import ReviewerAgent
from app.agents.reviewer.input_builder import ReviewerInputBuilder
from app.agents.reviewer.schemas import ReviewerOutput, ReviewStatus
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class ReviewerService:
    """Service for reviewing content.

    Provides methods for reviewing different types of copy.
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
        self._input_builder = ReviewerInputBuilder()
        self._agent = ReviewerAgent()

    async def review_topic_intro(
        self,
        topic_id: int,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[ReviewerOutput | None, dict[str, Any]]:
        """Review a topic intro.

        Args:
            topic_id: ID of the topic.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (ReviewerOutput or None, metadata).
        """
        return await self._review_copy(
            topic_id=topic_id,
            copy_type="topic_intro",
            copy_body=copy_body,
            copy_id=copy_id,
            historian_output=historian_output,
            analyst_output=analyst_output,
        )

    async def review_feed_card(
        self,
        topic_id: int,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[ReviewerOutput | None, dict[str, Any]]:
        """Review a feed card.

        Args:
            topic_id: ID of the topic.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (ReviewerOutput or None, metadata).
        """
        return await self._review_copy(
            topic_id=topic_id,
            copy_type="feed_card",
            copy_body=copy_body,
            copy_id=copy_id,
            historian_output=historian_output,
            analyst_output=analyst_output,
        )

    async def review_trend_card(
        self,
        topic_id: int,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[ReviewerOutput | None, dict[str, Any]]:
        """Review a trend card.

        Args:
            topic_id: ID of the topic.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (ReviewerOutput or None, metadata).
        """
        return await self._review_copy(
            topic_id=topic_id,
            copy_type="trend_card",
            copy_body=copy_body,
            copy_id=copy_id,
            historian_output=historian_output,
            analyst_output=analyst_output,
        )

    async def review_report_section(
        self,
        topic_id: int,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[ReviewerOutput | None, dict[str, Any]]:
        """Review a report section.

        Args:
            topic_id: ID of the topic.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (ReviewerOutput or None, metadata).
        """
        return await self._review_copy(
            topic_id=topic_id,
            copy_type="report_section",
            copy_body=copy_body,
            copy_id=copy_id,
            historian_output=historian_output,
            analyst_output=analyst_output,
        )

    async def _review_copy(
        self,
        topic_id: int,
        copy_type: str,
        copy_body: dict[str, Any],
        *,
        copy_id: int | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
    ) -> tuple[ReviewerOutput | None, dict[str, Any]]:
        """Internal method to review copy.

        Args:
            topic_id: ID of the topic.
            copy_type: Type of copy.
            copy_body: The copy content to review.
            copy_id: Optional copy ID.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.

        Returns:
            Tuple of (ReviewerOutput or None, metadata).
        """
        topic = await self._get_topic(topic_id)
        if topic is None:
            return None, {"error": "Topic not found"}

        representative_items = await self._get_representative_items(topic_id)
        timeline_points = await self._get_timeline_points(topic_id)

        reviewer_input = self._input_builder.build_review_input(
            topic=topic,
            copy_type=copy_type,
            copy_body=copy_body,
            copy_id=copy_id,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            timeline_points=timeline_points,
        )

        output, meta = await self._agent.review(reviewer_input)
        return output, meta or {}

    async def _get_topic(self, topic_id: int) -> "TopicReadDTO | None":
        """Get topic by ID."""
        if self._uow is None or self._uow.topics is None:
            return None
        return await self._uow.topics.get_by_id(topic_id)

    async def _get_representative_items(
        self,
        topic_id: int,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get representative items for a topic."""
        return []

    async def _get_timeline_points(
        self,
        topic_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get timeline points for a topic."""
        return []
