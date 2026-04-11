"""NormalizedItem ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import BoardType, ContentType
from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class NormalizedItem(IDMixin, TimestampMixin, Base):
    """Normalized content ready for topic clustering."""

    __tablename__ = "normalized_items"

    raw_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_items.id"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    content_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ContentType.ARTICLE,
    )
    board_type_candidate: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=BoardType.GENERAL,
        index=True,
    )
    quality_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0,
    )
    ai_relevance_score: Mapped[float] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0,
    )
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
