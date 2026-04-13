"""Entity Memory ORM model for long-term entity memory."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class EntityMemory(IDMixin, TimestampMixin, Base):
    """Long-term memory for an entity.

    Stores historical context, related topics, and key milestones
    for an entity over time.
    """

    __tablename__ = "entity_memories"

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    related_topic_ids_json: Mapped[list[int]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    milestones_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    recent_signals_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
