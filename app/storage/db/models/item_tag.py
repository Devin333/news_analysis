"""Item-Tag relationship ORM model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base


class ItemTag(Base):
    """Item-Tag relationship entity.

    Links normalized items to tags with confidence scores.
    """

    __tablename__ = "item_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("normalized_items.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    # Confidence score (0.0 to 1.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Source of the tag (rule, llm, manual)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="rule")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_item_tags_item_id", "item_id"),
        Index("ix_item_tags_tag_id", "tag_id"),
        Index("ix_item_tags_item_tag", "item_id", "tag_id", unique=True),
    )
