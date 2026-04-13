"""Topic Insight ORM model for storing analyst output."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class TopicInsight(IDMixin, TimestampMixin, Base):
    """Insight record for a topic from Analyst Agent.

    Stores value analysis, judgements, and recommendations.
    """

    __tablename__ = "topic_insights"

    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Core analysis
    why_it_matters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    system_judgement: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Audience
    likely_audience_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    # Follow-up points
    follow_up_points_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    # Trend analysis
    trend_stage: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    trend_momentum: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    # Confidence
    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    # Evidence
    evidence_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    key_signals_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    # Metadata
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    source_agent: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="analyst",
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
