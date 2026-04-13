"""Report ORM model.

Stores generated reports (daily/weekly).
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class Report(Base):
    """Report model.

    Stores daily and weekly reports.
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Report type: daily, weekly
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Report date (the date/week the report covers)
    report_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # For weekly reports, store the week key (e.g., "2026-W15")
    week_key: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Sections stored as JSON
    sections_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Editorial conclusion
    editorial_conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    topic_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Generation metadata
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1")
    source_agent: Mapped[str] = mapped_column(String(50), nullable=False, default="report_editor")

    # Status: draft, pending_review, approved, published, archived
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Review status
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, type={self.report_type}, date={self.report_date})>"
