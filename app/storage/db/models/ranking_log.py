"""Ranking Log ORM model.

Stores ranking computation logs for debugging and analysis.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class RankingLog(Base):
    """Ranking log model.

    Stores ranking computation results for debugging.
    """

    __tablename__ = "ranking_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Target
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Context
    ranking_context: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Features
    features_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Score
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    component_scores_json: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)

    # Explanation
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_factors_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Rank (if part of a batch)
    rank_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batch_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Request metadata
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    user_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<RankingLog(id={self.id}, target={self.target_type}:{self.target_id}, "
            f"context={self.ranking_context}, score={self.final_score:.3f})>"
        )
