"""Report view contracts for frontend display.

Defines the structure of report data as displayed to users.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportTopicCardView(BaseModel):
    """View model for a topic card within a report."""

    topic_id: int
    title: str
    summary: str | None = None
    why_it_matters: str | None = None
    trend_stage: str | None = None
    heat_score: float = 0.0
    tags: list[str] = Field(default_factory=list)


class ReportSectionView(BaseModel):
    """View model for a report section."""

    section_id: str
    section_title: str
    section_intro: str
    key_points: list[str] = Field(default_factory=list)
    topic_cards: list[ReportTopicCardView] = Field(default_factory=list)
    closing_note: str | None = None
    editorial_note: str | None = None


class ReportSummaryView(BaseModel):
    """Lightweight view for report list display."""

    id: int
    report_type: str
    report_date: datetime
    title: str
    executive_summary_preview: str  # First 200 chars
    topic_count: int = 0
    status: str = "draft"
    generated_at: datetime | None = None


class ReportDetailView(BaseModel):
    """Full view model for a report.

    Contains all information needed to render a complete report.
    """

    # Identification
    id: int | None = None
    report_type: str
    report_date: datetime
    week_key: str | None = None  # For weekly reports

    # Content
    title: str
    executive_summary: str
    key_highlights: list[str] = Field(default_factory=list)

    # Sections
    sections: list[ReportSectionView] = Field(default_factory=list)

    # Editorial
    editorial_conclusion: str | None = None
    watch_next: list[str] = Field(default_factory=list)

    # Topic cards (flat list for quick access)
    topic_cards: list[ReportTopicCardView] = Field(default_factory=list)

    # Metrics
    topic_count: int = 0
    trend_count: int = 0

    # Status
    status: str = "draft"
    review_status: str | None = None

    # Timestamps
    generated_at: datetime | None = None
    published_at: datetime | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyReportView(ReportDetailView):
    """View model specifically for daily reports."""

    report_type: str = "daily"

    # Daily-specific fields
    top_story: ReportTopicCardView | None = None
    trending_topics: list[ReportTopicCardView] = Field(default_factory=list)
    notable_releases: list[str] = Field(default_factory=list)


class WeeklyReportView(ReportDetailView):
    """View model specifically for weekly reports."""

    report_type: str = "weekly"

    # Weekly-specific fields
    week_start: datetime | None = None
    week_end: datetime | None = None
    emerging_trends: list[ReportTopicCardView] = Field(default_factory=list)
    week_in_review: str | None = None
    category_breakdown: dict[str, int] = Field(default_factory=dict)


class ReportListView(BaseModel):
    """View model for a list of reports."""

    reports: list[ReportSummaryView] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False

    # Filters
    report_type_filter: str | None = None


class ReportPageView(BaseModel):
    """View model for the reports landing page."""

    # Latest reports
    latest_daily: ReportSummaryView | None = None
    latest_weekly: ReportSummaryView | None = None

    # Recent reports
    recent_daily: list[ReportSummaryView] = Field(default_factory=list)
    recent_weekly: list[ReportSummaryView] = Field(default_factory=list)

    # Stats
    total_daily_reports: int = 0
    total_weekly_reports: int = 0

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)


def build_report_detail_view(
    report: Any,
    topic_cards: list[dict[str, Any]] | None = None,
) -> ReportDetailView:
    """Build a ReportDetailView from report data.

    Args:
        report: Report data (DTO or dict).
        topic_cards: Optional list of topic card data.

    Returns:
        ReportDetailView.
    """
    # Handle both DTO and dict
    if hasattr(report, "model_dump"):
        data = report.model_dump()
    else:
        data = report

    # Build sections
    sections = []
    for section_data in data.get("sections", []):
        topic_cards_in_section = []
        for ts in section_data.get("topic_summaries", []):
            topic_cards_in_section.append(ReportTopicCardView(
                topic_id=ts.get("topic_id", 0),
                title=ts.get("title", ""),
                summary=ts.get("summary"),
                why_it_matters=ts.get("why_it_matters"),
                trend_stage=ts.get("trend_stage"),
                heat_score=ts.get("heat_score", 0.0),
            ))

        sections.append(ReportSectionView(
            section_id=section_data.get("section_id", ""),
            section_title=section_data.get("section_title", ""),
            section_intro=section_data.get("section_intro", ""),
            key_points=section_data.get("key_points", []),
            topic_cards=topic_cards_in_section,
            closing_note=section_data.get("closing_note"),
            editorial_note=section_data.get("editorial_note"),
        ))

    # Build topic cards from provided data
    cards = []
    if topic_cards:
        for tc in topic_cards:
            cards.append(ReportTopicCardView(
                topic_id=tc.get("id", 0),
                title=tc.get("title", ""),
                summary=tc.get("summary"),
                why_it_matters=tc.get("why_it_matters"),
                trend_stage=tc.get("trend_stage"),
                heat_score=tc.get("heat_score", 0.0),
                tags=tc.get("tags", []),
            ))

    # Extract metadata fields
    metadata = data.get("metadata", {})

    return ReportDetailView(
        id=data.get("id"),
        report_type=data.get("report_type", "daily"),
        report_date=data.get("report_date", datetime.utcnow()),
        title=data.get("title", ""),
        executive_summary=data.get("executive_summary", ""),
        key_highlights=metadata.get("key_highlights", []),
        sections=sections,
        editorial_conclusion=metadata.get("editorial_conclusion"),
        watch_next=metadata.get("watch_next_week", []),
        topic_cards=cards,
        topic_count=data.get("topic_count", 0),
        status=data.get("status", "draft"),
        generated_at=data.get("generated_at"),
        metadata=metadata,
    )


def build_report_summary_view(report: Any) -> ReportSummaryView:
    """Build a ReportSummaryView from report data.

    Args:
        report: Report data.

    Returns:
        ReportSummaryView.
    """
    if hasattr(report, "model_dump"):
        data = report.model_dump()
    else:
        data = report

    summary = data.get("executive_summary", "")
    preview = summary[:200] + "..." if len(summary) > 200 else summary

    return ReportSummaryView(
        id=data.get("id", 0),
        report_type=data.get("report_type", "daily"),
        report_date=data.get("report_date", datetime.utcnow()),
        title=data.get("title", ""),
        executive_summary_preview=preview,
        topic_count=data.get("topic_count", 0),
        status=data.get("status", "draft"),
        generated_at=data.get("generated_at"),
    )
