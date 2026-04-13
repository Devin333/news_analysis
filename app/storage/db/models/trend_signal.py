"""Trend Signal ORM model.

Stores detected trend signals for topics.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class TrendSignal(Base):
    """Trend signal model.

    Stores detected trend signals for topics.
    """

    __tablename__ = "trend_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Signal type: growth, diversity, recency, release, discussion, etc.
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Time window
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Evidence
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    # Detection metadata
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Stage label: emerging, growing, peak, stable, declining
    stage_label: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Status: active, expired, superseded
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<TrendSignal(id={self.id}, topic_id={self.topic_id}, type={self.signal_type})>"
