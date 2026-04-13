"""Topic-Tag relationship ORM model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base


class TopicTag(Base):
    """Topic-Tag relationship entity.

    Links topics to tags with aggregated confidence scores.
    """

    __tablename__ = "topic_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    # Aggregated confidence score (0.0 to 1.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Number of items in topic with this tag
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Source of the tag (aggregated, manual)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="aggregated")

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

    __table_args__ = (
        Index("ix_topic_tags_topic_id", "topic_id"),
        Index("ix_topic_tags_tag_id", "tag_id"),
        Index("ix_topic_tags_topic_tag", "topic_id", "tag_id", unique=True),
    )
