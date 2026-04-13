"""Subscription service for managing subscriptions."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.subscription import (
    MatchMode,
    NotifyFrequency,
    SubscriptionCreateDTO,
    SubscriptionMatchDTO,
    SubscriptionMatchResultDTO,
    SubscriptionReadDTO,
    SubscriptionStatus,
    SubscriptionType,
    SubscriptionUpdateDTO,
)

if TYPE_CHECKING:
    from app.storage.repositories.subscription_repository import (
        SubscriptionEventRepository,
        SubscriptionRepository,
    )
    from app.subscription.matcher import SubscriptionMatcher

logger = get_logger(__name__)


class SubscriptionService:
    """Service for managing subscriptions.

    Handles:
    - Creating/updating/deleting subscriptions
    - Matching content against subscriptions
    - Recording match events
    """

    def __init__(
        self,
        subscription_repo: "SubscriptionRepository | None" = None,
        event_repo: "SubscriptionEventRepository | None" = None,
        matcher: "SubscriptionMatcher | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            subscription_repo: Subscription repository.
            event_repo: Event repository.
            matcher: Subscription matcher.
        """
        self._subscription_repo = subscription_repo
        self._event_repo = event_repo
        self._matcher = matcher

    async def create_subscription(
        self,
        data: SubscriptionCreateDTO,
    ) -> SubscriptionReadDTO:
        """Create a new subscription.

        Args:
            data: Subscription creation data.

        Returns:
            Created subscription.
        """
        if not self._subscription_repo:
            raise RuntimeError("Subscription repository not configured")

        subscription = await self._subscription_repo.create(
            subscription_type=data.subscription_type.value,
            user_key=data.user_key,
            query=data.query,
            tags=data.tags,
            board_type=data.board_type,
            entity_id=data.entity_id,
            topic_id=data.topic_id,
            name=data.name,
            notify_email=data.notify_email,
            notify_frequency=data.notify_frequency.value,
            min_score=data.min_score,
            match_mode=data.match_mode.value,
            metadata=data.metadata,
        )

        logger.info(f"Created subscription {subscription.id} for user {data.user_key}")
        return self._to_read_dto(subscription)

    async def get_subscription(
        self,
        subscription_id: int,
    ) -> SubscriptionReadDTO | None:
        """Get a subscription by ID.

        Args:
            subscription_id: Subscription ID.

        Returns:
            Subscription or None.
        """
        if not self._subscription_repo:
            return None

        subscription = await self._subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            return None

        return self._to_read_dto(subscription)

    async def list_subscriptions(
        self,
        user_key: str,
        *,
        status: SubscriptionStatus | None = None,
        limit: int = 50,
    ) -> list[SubscriptionReadDTO]:
        """List subscriptions for a user.

        Args:
            user_key: User identifier.
            status: Optional status filter.
            limit: Maximum subscriptions.

        Returns:
            List of subscriptions.
        """
        if not self._subscription_repo:
            return []

        subscriptions = await self._subscription_repo.list_by_user(
            user_key,
            status=status.value if status else None,
            limit=limit,
        )

        return [self._to_read_dto(s) for s in subscriptions]

    async def update_subscription(
        self,
        subscription_id: int,
        data: SubscriptionUpdateDTO,
    ) -> SubscriptionReadDTO | None:
        """Update a subscription.

        Args:
            subscription_id: Subscription ID.
            data: Update data.

        Returns:
            Updated subscription or None.
        """
        if not self._subscription_repo:
            return None

        subscription = await self._subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            return None

        # Update fields
        if data.status is not None:
            await self._subscription_repo.update_status(
                subscription_id, data.status.value
            )

        # Refresh and return
        subscription = await self._subscription_repo.get_by_id(subscription_id)
        return self._to_read_dto(subscription) if subscription else None

    async def disable_subscription(
        self,
        subscription_id: int,
    ) -> bool:
        """Disable a subscription.

        Args:
            subscription_id: Subscription ID.

        Returns:
            True if disabled.
        """
        if not self._subscription_repo:
            return False

        return await self._subscription_repo.update_status(
            subscription_id, "disabled"
        )

    async def delete_subscription(
        self,
        subscription_id: int,
    ) -> bool:
        """Delete a subscription.

        Args:
            subscription_id: Subscription ID.

        Returns:
            True if deleted.
        """
        if not self._subscription_repo:
            return False

        return await self._subscription_repo.delete(subscription_id)

    async def match_topic_against_subscriptions(
        self,
        topic_id: int,
        topic_title: str,
        topic_summary: str | None = None,
        topic_tags: list[str] | None = None,
        board_type: str | None = None,
    ) -> SubscriptionMatchResultDTO:
        """Match a topic against all active subscriptions.

        Args:
            topic_id: Topic ID.
            topic_title: Topic title.
            topic_summary: Topic summary.
            topic_tags: Topic tags.
            board_type: Topic board type.

        Returns:
            Match result with matched subscriptions.
        """
        if not self._subscription_repo or not self._matcher:
            return SubscriptionMatchResultDTO(
                content_type="topic",
                content_id=topic_id,
            )

        # Get active subscriptions
        subscriptions = await self._subscription_repo.list_active()

        matched_subscriptions = []
        match_details = []

        for subscription in subscriptions:
            match_result = self._matcher.match_topic(
                subscription=subscription,
                topic_title=topic_title,
                topic_summary=topic_summary,
                topic_tags=topic_tags or [],
                board_type=board_type,
            )

            if match_result["matched"]:
                matched_subscriptions.append(subscription.id)
                match_details.append({
                    "subscription_id": subscription.id,
                    "score": match_result["score"],
                    "reason": match_result["reason"],
                    "matched_fields": match_result["matched_fields"],
                })

                # Record event
                if self._event_repo:
                    await self.record_subscription_hit(
                        subscription_id=subscription.id,
                        target_type="topic",
                        target_id=topic_id,
                        match_score=match_result["score"],
                        match_reason=match_result["reason"],
                        matched_fields=match_result["matched_fields"],
                        matched_tags=match_result.get("matched_tags", []),
                    )

        return SubscriptionMatchResultDTO(
            content_type="topic",
            content_id=topic_id,
            matched_subscriptions=matched_subscriptions,
            match_details=match_details,
            total_matches=len(matched_subscriptions),
        )

    async def record_subscription_hit(
        self,
        subscription_id: int,
        target_type: str,
        target_id: int,
        *,
        match_score: float = 0.0,
        match_reason: str | None = None,
        matched_fields: list[str] | None = None,
        matched_tags: list[str] | None = None,
    ) -> None:
        """Record a subscription match event.

        Args:
            subscription_id: Subscription ID.
            target_type: Type of matched content.
            target_id: ID of matched content.
            match_score: Match score.
            match_reason: Reason for match.
            matched_fields: Fields that matched.
            matched_tags: Tags that matched.
        """
        if not self._event_repo or not self._subscription_repo:
            return

        await self._event_repo.create(
            subscription_id=subscription_id,
            target_type=target_type,
            target_id=target_id,
            match_score=match_score,
            match_reason=match_reason,
            matched_fields=matched_fields,
            matched_tags=matched_tags,
        )

        # Update last matched timestamp
        await self._subscription_repo.update_last_matched(subscription_id)

    async def get_subscription_matches(
        self,
        subscription_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[SubscriptionMatchDTO]:
        """Get match events for a subscription.

        Args:
            subscription_id: Subscription ID.
            unread_only: Only return unread events.
            limit: Maximum events.

        Returns:
            List of match events.
        """
        if not self._event_repo:
            return []

        events = await self._event_repo.list_by_subscription(
            subscription_id,
            unread_only=unread_only,
            limit=limit,
        )

        return [
            SubscriptionMatchDTO(
                id=e.id,
                subscription_id=e.subscription_id,
                target_type=e.target_type,
                target_id=e.target_id,
                match_score=e.match_score,
                match_reason=e.match_reason,
                matched_fields=e.matched_fields_json,
                matched_tags=e.matched_tags_json,
                notification_status=e.notification_status,
                is_read=e.is_read,
                created_at=e.created_at,
            )
            for e in events
        ]

    async def mark_match_as_read(
        self,
        event_id: int,
    ) -> bool:
        """Mark a match event as read.

        Args:
            event_id: Event ID.

        Returns:
            True if marked.
        """
        if not self._event_repo:
            return False

        return await self._event_repo.mark_as_read(event_id)

    def _to_read_dto(self, subscription: Any) -> SubscriptionReadDTO:
        """Convert subscription model to DTO.

        Args:
            subscription: Subscription model.

        Returns:
            SubscriptionReadDTO.
        """
        return SubscriptionReadDTO(
            id=subscription.id,
            subscription_type=SubscriptionType(subscription.subscription_type),
            user_key=subscription.user_key,
            query=subscription.query,
            tags=subscription.tags_json or [],
            board_type=subscription.board_type,
            entity_id=subscription.entity_id,
            topic_id=subscription.topic_id,
            name=subscription.name,
            status=SubscriptionStatus(subscription.status),
            notify_email=subscription.notify_email,
            notify_frequency=NotifyFrequency(subscription.notify_frequency),
            min_score=subscription.min_score,
            match_mode=MatchMode(subscription.match_mode),
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            last_matched_at=subscription.last_matched_at,
        )
