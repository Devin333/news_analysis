"""Topic Timeline Event ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class TopicTimelineEvent(IDMixin, TimestampMixin, Base):
    """Timeline event for a topic.

    Represents a significant event in the history of a topic,
    such as first appearance, major updates, releases, etc.
    """

    __tablename__ = "topic_timeline_events"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    # first_seen, release_published, paper_published, repo_created,
    # community_discussion_spike, topic_summary_changed, milestone, etc.
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Reference to the source item that triggered this event
    source_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Type of source (item, snapshot, judgement, external)
    source_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    # Importance score for ranking/filtering (0-1)
    importance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    # Whether this is a milestone event
    is_milestone: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
