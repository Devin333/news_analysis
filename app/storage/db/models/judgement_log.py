"""Judgement Log ORM model for agent judgement history."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.base import Base
from app.storage.db.models_base import IDMixin, TimestampMixin


class JudgementLog(IDMixin, TimestampMixin, Base):
    """Record of a system judgement made by an agent.

    Stores historical judgements for validation and trend analysis.
    """

    __tablename__ = "judgement_logs"

    # topic, entity, item
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )
    target_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    # importance, trend, classification, sentiment, etc.
    judgement_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    judgement: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    evidence_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    # For later validation of judgement accuracy
    later_outcome: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
