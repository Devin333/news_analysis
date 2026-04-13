"""Subscription Event ORM model.

Stores subscription match events and notifications.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class SubscriptionEvent(Base):
    """Subscription event model.

    Records each time a subscription matches content.
    """

    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Subscription reference
    subscription_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Matched content
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # topic, item, entity, report, trend
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Match details
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_fields_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    matched_tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Notification status
    notification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    # pending, sent, failed, skipped
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # User interaction
    is_read: Mapped[bool] = mapped_column(default=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_dismissed: Mapped[bool] = mapped_column(default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SubscriptionEvent(id={self.id}, subscription_id={self.subscription_id}, "
            f"target={self.target_type}:{self.target_id}, score={self.match_score:.2f})>"
        )
