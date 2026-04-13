"""Tag ORM model."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base


class Tag(Base):
    """Tag entity for content classification.

    Tags are used to categorize and classify content items and topics.
    They support hierarchical relationships through parent_tag_id.
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Tag name (display name)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Normalized name for matching (lowercase, no spaces)
    normalized_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    # Tag type for categorization
    # Values: company, model, framework, task, method, source, board, content_type, technology_domain
    tag_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Comma-separated list of aliases for matching
    aliases: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Description of the tag
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Parent tag for hierarchical relationships
    parent_tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tags.id"), nullable=True
    )

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
        Index("ix_tags_tag_type", "tag_type"),
        Index("ix_tags_parent_tag_id", "parent_tag_id"),
        Index("ix_tags_normalized_name", "normalized_name"),
    )
