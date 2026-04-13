"""Topic Copy ORM model.

Stores generated copy for topics (feed cards, intros, etc.).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class TopicCopy(Base):
    """Topic copy model.

    Stores different types of generated copy for topics.
    """

    __tablename__ = "topic_copies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Copy type: feed_card, topic_intro, trend_card, report_section
    copy_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Main content
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Generation metadata
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    source_agent: Mapped[str] = mapped_column(String(50), nullable=False, default="writer")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

    # Status: draft, pending_review, approved, rejected, published
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Review tracking
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<TopicCopy(id={self.id}, topic_id={self.topic_id}, type={self.copy_type})>"
