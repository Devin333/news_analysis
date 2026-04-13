"""Subscription ORM model.

Stores user subscriptions for tracking topics, entities, and queries.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class Subscription(Base):
    """Subscription model.

    Stores subscription configurations for tracking content.
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Subscription type: query, tag, entity, topic, board
    subscription_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Query/pattern to match
    query: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tags to match (JSON array)
    tags_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Board type filter
    board_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Entity ID (for entity subscriptions)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Topic ID (for topic subscriptions)
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # User identifier (email, key, or user_id)
    user_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Subscription name/label
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status: active, paused, disabled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)

    # Notification settings
    notify_email: Mapped[bool] = mapped_column(default=True)
    notify_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    # immediate, daily, weekly

    # Match settings
    min_score: Mapped[float] = mapped_column(default=0.5)
    match_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="any")
    # any, all, exact

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Subscription(id={self.id}, type={self.subscription_type}, "
            f"user={self.user_key}, status={self.status})>"
        )
