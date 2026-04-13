"""Report Topic Link ORM model.

Links reports to their included topics.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.db.models_base import Base


class ReportTopicLink(Base):
    """Report-Topic link model.

    Associates topics with reports and stores their position/role.
    """

    __tablename__ = "report_topic_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position in report
    section_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Role in report: featured, main, supporting, mention
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="main")

    # Inclusion reason
    inclusion_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Scores at time of inclusion
    heat_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Additional metadata
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<ReportTopicLink(report={self.report_id}, topic={self.topic_id}, role={self.role})>"
