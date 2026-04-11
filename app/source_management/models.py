"""Source ORM model."""

from typing import Any

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import SourceType
from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class Source(IDMixin, TimestampMixin, Base):
    """Source represents a content origin (RSS feed, website, etc.)."""

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SourceType.RSS,
    )
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    trust_score: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=0.5,
    )
    fetch_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    def __repr__(self) -> str:
        return f"<Source id={self.id} name={self.name!r} type={self.source_type}>"
