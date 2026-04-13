"""Topic Snapshot ORM model for point-in-time topic state."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class TopicSnapshot(IDMixin, TimestampMixin, Base):
    """Point-in-time snapshot of a topic.

    Captures the state of a topic at a specific moment,
    allowing historical tracking of topic evolution.
    """

    __tablename__ = "topic_snapshots"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    why_it_matters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    system_judgement: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    heat_score: Mapped[float] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=0.0,
    )
    trend_score: Mapped[float] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        default=0.0,
    )
    item_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    representative_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("normalized_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeline_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
