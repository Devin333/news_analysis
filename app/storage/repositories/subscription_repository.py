"""Subscription repository implementation."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.storage.db.models.subscription import Subscription
from app.storage.db.models.subscription_event import SubscriptionEvent

logger = get_logger(__name__)


class SubscriptionRepository:
    """Repository for subscription operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        subscription_type: str,
        user_key: str,
        *,
        query: str | None = None,
        tags: list[str] | None = None,
        board_type: str | None = None,
        entity_id: int | None = None,
        topic_id: int | None = None,
        name: str | None = None,
        notify_email: bool = True,
        notify_frequency: str = "daily",
        min_score: float = 0.5,
        match_mode: str = "any",
        metadata: dict[str, Any] | None = None,
    ) -> Subscription:
        """Create a subscription.

        Args:
            subscription_type: Type of subscription.
            user_key: User identifier.
            query: Query string for matching.
            tags: Tags to match.
            board_type: Board type filter.
            entity_id: Entity ID for entity subscriptions.
            topic_id: Topic ID for topic subscriptions.
            name: Subscription name.
            notify_email: Whether to send email notifications.
            notify_frequency: Notification frequency.
            min_score: Minimum match score.
            match_mode: Match mode (any, all, exact).
            metadata: Additional metadata.

        Returns:
            Created Subscription.
        """
        model = Subscription(
            subscription_type=subscription_type,
            user_key=user_key,
            query=query,
            tags_json=tags or [],
            board_type=board_type,
            entity_id=entity_id,
            topic_id=topic_id,
            name=name,
            status="active",
            notify_email=notify_email,
            notify_frequency=notify_frequency,
            min_score=min_score,
            match_mode=match_mode,
            metadata_json=metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(f"Created subscription {model.id} for user {user_key}")
        return model

    async def get_by_id(self, subscription_id: int) -> Subscription | None:
        """Get subscription by ID.

        Args:
            subscription_id: Subscription ID.

        Returns:
            Subscription or None.
        """
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_key: str,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Subscription]:
        """List subscriptions for a user.

        Args:
            user_key: User identifier.
            status: Optional status filter.
            limit: Maximum subscriptions.

        Returns:
            List of Subscription.
        """
        stmt = select(Subscription).where(Subscription.user_key == user_key)

        if status:
            stmt = stmt.where(Subscription.status == status)

        stmt = stmt.order_by(Subscription.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_active(
        self,
        *,
        subscription_type: str | None = None,
        limit: int = 1000,
    ) -> list[Subscription]:
        """List active subscriptions.

        Args:
            subscription_type: Optional type filter.
            limit: Maximum subscriptions.

        Returns:
            List of active Subscription.
        """
        stmt = select(Subscription).where(Subscription.status == "active")

        if subscription_type:
            stmt = stmt.where(Subscription.subscription_type == subscription_type)

        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        subscription_id: int,
        status: str,
    ) -> bool:
        """Update subscription status.

        Args:
            subscription_id: Subscription ID.
            status: New status.

        Returns:
            True if updated.
        """
        stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(status=status, updated_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def update_last_matched(
        self,
        subscription_id: int,
    ) -> bool:
        """Update last matched timestamp.

        Args:
            subscription_id: Subscription ID.

        Returns:
            True if updated.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(last_matched_at=now, updated_at=now)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def delete(self, subscription_id: int) -> bool:
        """Delete a subscription.

        Args:
            subscription_id: Subscription ID.

        Returns:
            True if deleted.
        """
        subscription = await self.get_by_id(subscription_id)
        if subscription:
            await self._session.delete(subscription)
            await self._session.flush()
            return True
        return False


class SubscriptionEventRepository:
    """Repository for subscription event operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Async database session.
        """
        self._session = session

    async def create(
        self,
        subscription_id: int,
        target_type: str,
        target_id: int,
        *,
        match_score: float = 0.0,
        match_reason: str | None = None,
        matched_fields: list[str] | None = None,
        matched_tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SubscriptionEvent:
        """Create a subscription event.

        Args:
            subscription_id: Subscription ID.
            target_type: Type of matched content.
            target_id: ID of matched content.
            match_score: Match score.
            match_reason: Reason for match.
            matched_fields: Fields that matched.
            matched_tags: Tags that matched.
            metadata: Additional metadata.

        Returns:
            Created SubscriptionEvent.
        """
        model = SubscriptionEvent(
            subscription_id=subscription_id,
            target_type=target_type,
            target_id=target_id,
            match_score=match_score,
            match_reason=match_reason,
            matched_fields_json=matched_fields or [],
            matched_tags_json=matched_tags or [],
            notification_status="pending",
            metadata_json=metadata,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        logger.info(
            f"Created subscription event for subscription {subscription_id}, "
            f"target {target_type}:{target_id}"
        )
        return model

    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[SubscriptionEvent]:
        """List events for a subscription.

        Args:
            subscription_id: Subscription ID.
            unread_only: Only return unread events.
            limit: Maximum events.

        Returns:
            List of SubscriptionEvent.
        """
        stmt = select(SubscriptionEvent).where(
            SubscriptionEvent.subscription_id == subscription_id
        )

        if unread_only:
            stmt = stmt.where(SubscriptionEvent.is_read == False)

        stmt = stmt.order_by(SubscriptionEvent.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_notifications(
        self,
        *,
        limit: int = 100,
    ) -> list[SubscriptionEvent]:
        """List events pending notification.

        Args:
            limit: Maximum events.

        Returns:
            List of pending SubscriptionEvent.
        """
        stmt = (
            select(SubscriptionEvent)
            .where(SubscriptionEvent.notification_status == "pending")
            .order_by(SubscriptionEvent.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_read(self, event_id: int) -> bool:
        """Mark event as read.

        Args:
            event_id: Event ID.

        Returns:
            True if updated.
        """
        stmt = (
            update(SubscriptionEvent)
            .where(SubscriptionEvent.id == event_id)
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def update_notification_status(
        self,
        event_id: int,
        status: str,
    ) -> bool:
        """Update notification status.

        Args:
            event_id: Event ID.
            status: New status.

        Returns:
            True if updated.
        """
        values: dict[str, Any] = {"notification_status": status}
        if status == "sent":
            values["notified_at"] = datetime.now(timezone.utc)

        stmt = (
            update(SubscriptionEvent)
            .where(SubscriptionEvent.id == event_id)
            .values(**values)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def count_unread(self, subscription_id: int) -> int:
        """Count unread events for a subscription.

        Args:
            subscription_id: Subscription ID.

        Returns:
            Count of unread events.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(SubscriptionEvent)
            .where(
                SubscriptionEvent.subscription_id == subscription_id,
                SubscriptionEvent.is_read == False,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
