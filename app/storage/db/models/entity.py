"""Entity ORM model for named entities."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class Entity(IDMixin, TimestampMixin, Base):
    """Named entity (person, organization, product, etc.).

    Entities are extracted from content and tracked across topics.
    """

    __tablename__ = "entities"

    # person, organization, product, technology, location, etc.
    entity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    normalized_name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        index=True,
    )
    aliases_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
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
    activity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
