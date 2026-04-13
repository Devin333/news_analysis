"""ReportEditor Agent output schemas.

Defines the structured output formats for the ReportEditor Agent.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(StrEnum):
    """Type of report."""

    DAILY = "daily"
    WEEKLY = "weekly"


class ReportSectionOutput(BaseModel):
    """Output for a single report section."""

    section_id: str = Field(
        description="Unique identifier for the section"
    )
    section_title: str = Field(
        description="Title for this section"
    )
    section_intro: str = Field(
        description="Introduction paragraph for the section"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points covered in this section (3-5 items)"
    )
    topic_highlights: list[dict[str, str]] = Field(
        default_factory=list,
        description="Brief highlights for each topic in section"
    )
    closing_note: str | None = Field(
        default=None,
        description="Optional closing remarks for the section"
    )


class ReportEditorOutput(BaseModel):
    """Output schema for ReportEditor Agent."""

    # Report metadata
    report_type: ReportType = Field(
        description="Type of report (daily/weekly)"
    )
    report_title: str = Field(
        description="Main title for the report"
    )

    # Executive summary
    executive_summary: str = Field(
        description="Executive summary (2-3 paragraphs)"
    )
    key_highlights: list[str] = Field(
        default_factory=list,
        description="Top 3-5 highlights from the report"
    )

    # Sections
    sections: list[ReportSectionOutput] = Field(
        default_factory=list,
        description="Report sections"
    )

    # Editorial content
    editorial_conclusion: str = Field(
        description="Editorial conclusion and outlook"
    )
    watch_next_week: list[str] = Field(
        default_factory=list,
        description="Topics to watch in the coming period"
    )

    # Metadata
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in the report quality"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicSummaryInput(BaseModel):
    """Input summary for a topic."""

    topic_id: int
    title: str
    summary: str | None = None
    why_it_matters: str | None = None
    trend_stage: str | None = None
    heat_score: float = 0.0
    trend_score: float = 0.0
    item_count: int = 0
    source_count: int = 0
    board_type: str | None = None
    tags: list[str] = Field(default_factory=list)


class TrendSignalInput(BaseModel):
    """Input for a trend signal."""

    topic_id: int
    signal_type: str
    strength: float
    description: str


class ReportEditorInput(BaseModel):
    """Input schema for ReportEditor Agent."""

    # Report type
    report_type: ReportType
    report_date: datetime

    # For weekly reports
    week_start: datetime | None = None
    week_end: datetime | None = None

    # Topics to include
    top_topics: list[TopicSummaryInput] = Field(
        default_factory=list,
        description="Top topics for the report"
    )

    # Trend signals
    trend_signals: list[TrendSignalInput] = Field(
        default_factory=list,
        description="Detected trend signals"
    )

    # High-confidence insights
    key_insights: list[str] = Field(
        default_factory=list,
        description="Key insights from analyst"
    )

    # Important events
    important_releases: list[str] = Field(
        default_factory=list,
        description="Important releases/announcements"
    )
    important_discussions: list[str] = Field(
        default_factory=list,
        description="Important discussions"
    )

    # Previous report context (for continuity)
    previous_report_summary: str | None = Field(
        default=None,
        description="Summary of previous report for continuity"
    )
    previous_watch_items: list[str] = Field(
        default_factory=list,
        description="Items flagged to watch from previous report"
    )

    # Additional context
    additional_context: dict[str, Any] = Field(default_factory=dict)
