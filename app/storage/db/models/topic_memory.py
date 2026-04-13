"""Topic Memory ORM model for long-term topic memory."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class TopicMemory(IDMixin, TimestampMixin, Base):
    """Long-term memory for a topic.

    Stores historical context, evolution status, and key milestones
    for a topic over time.
    """

    __tablename__ = "topic_memories"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # new, evolving, recurring, milestone
    historical_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="new",
    )
    # emerging, active, stable, declining
    current_stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="emerging",
    )
    history_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    key_milestones_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Store latest historian output
    latest_historian_output_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    historian_confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
