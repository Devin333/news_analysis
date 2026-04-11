"""RawItem ORM model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin


class RawItem(IDMixin, Base):
    """Raw collected content before normalization."""

    __tablename__ = "raw_items"

    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
