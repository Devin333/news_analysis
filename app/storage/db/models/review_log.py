"""Review Log ORM model.

Stores review results for content.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class ReviewLog(Base):
    """Review log model.

    Stores review results for topic copies.
    """

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Target
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    copy_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("topic_copies.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Review result
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)  # approve, revise, reject
    issues_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    missing_points_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    unsupported_claims_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    style_issues_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    revision_hints_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Summary
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

    # Source
    source_agent: Mapped[str] = mapped_column(String(50), nullable=False, default="reviewer")
    reviewer_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<ReviewLog(id={self.id}, target={self.target_type}:{self.target_id}, status={self.review_status})>"
