"""TopicItem association ORM model."""

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base


class TopicItem(Base):
    """Association table between topics and normalized items."""

    __tablename__ = "topic_items"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    link_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
