"""Topic ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class Topic(IDMixin, TimestampMixin, Base):
    """Topic represents a clustered group of related items."""

    __tablename__ = "topics"

    board_type: Mapped[str] = mapped_column(String(32), nullable=False, default="general", index=True)
    topic_type: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_items.id"),
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heat_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0.0)
    trend_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
