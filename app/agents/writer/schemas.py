"""Writer Agent output schemas.

Defines the structured output formats for the Writer Agent,
which generates different types of content copy.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CopyType(StrEnum):
    """Type of copy to generate."""

    FEED_CARD = "feed_card"
    TOPIC_INTRO = "topic_intro"
    TREND_CARD = "trend_card"
    REPORT_SECTION = "report_section"


class FeedCardCopyDTO(BaseModel):
    """Copy for a feed card display.

    Short, punchy content for feed/list views.
    """

    title: str = Field(
        description="Engaging title for the feed card"
    )
    short_summary: str = Field(
        description="1-2 sentence summary of the topic"
    )
    why_it_matters_short: str = Field(
        description="Brief explanation of importance (1 sentence)"
    )
    display_tags: list[str] = Field(
        default_factory=list,
        description="Tags to display on the card (max 3-4)"
    )
    audience_hint: str | None = Field(
        default=None,
        description="Who this is most relevant for"
    )
    call_to_action: str | None = Field(
        default=None,
        description="Optional CTA text"
    )


class TopicIntroCopyDTO(BaseModel):
    """Copy for a topic detail page introduction.

    More comprehensive content for topic pages.
    """

    headline: str = Field(
        description="Main headline for the topic page"
    )
    intro: str = Field(
        description="Introduction paragraph (2-3 sentences)"
    )
    key_takeaways: list[str] = Field(
        default_factory=list,
        description="3-5 key points about this topic"
    )
    why_it_matters: str = Field(
        description="Detailed explanation of importance"
    )
    what_changed_now: str = Field(
        description="What's new or different in current coverage"
    )
    background_context: str | None = Field(
        default=None,
        description="Historical or background context"
    )
    related_reading_hints: list[str] = Field(
        default_factory=list,
        description="Suggestions for related topics to explore"
    )


class TrendCardCopyDTO(BaseModel):
    """Copy for a trend card display.

    Content for trend/emerging topics pages.
    """

    trend_title: str = Field(
        description="Title highlighting the trend"
    )
    trend_summary: str = Field(
        description="Summary of the trend (2-3 sentences)"
    )
    signal_summary: str = Field(
        description="What signals indicate this trend"
    )
    stage_label: str = Field(
        description="Current stage label (e.g., 'Emerging', 'Growing')"
    )
    momentum_indicator: str | None = Field(
        default=None,
        description="Indicator of trend momentum"
    )
    watch_points: list[str] = Field(
        default_factory=list,
        description="What to watch for next"
    )


class ReportSectionCopyDTO(BaseModel):
    """Copy for a report section (daily/weekly report).

    Content for structured reports.
    """

    section_title: str = Field(
        description="Title for this report section"
    )
    section_intro: str = Field(
        description="Introduction to the section"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key points covered in this section"
    )
    topic_summaries: list[dict[str, str]] = Field(
        default_factory=list,
        description="Brief summaries of topics in this section"
    )
    closing_note: str | None = Field(
        default=None,
        description="Closing remarks or outlook"
    )
    editorial_note: str | None = Field(
        default=None,
        description="Optional editorial commentary"
    )


class WriterOutput(BaseModel):
    """Unified output wrapper for Writer Agent.

    Contains the generated copy and metadata.
    """

    copy_type: CopyType = Field(
        description="Type of copy generated"
    )
    topic_id: int = Field(
        description="ID of the topic this copy is for"
    )

    # The actual copy (one of these will be populated)
    feed_card: FeedCardCopyDTO | None = None
    topic_intro: TopicIntroCopyDTO | None = None
    trend_card: TrendCardCopyDTO | None = None
    report_section: ReportSectionCopyDTO | None = None

    # Metadata
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this copy was generated"
    )
    prompt_version: str = Field(
        default="v1",
        description="Version of the prompt used"
    )
    source_agent: str = Field(
        default="writer",
        description="Agent that generated this copy"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in the generated copy"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    def get_copy(self) -> BaseModel | None:
        """Get the actual copy based on copy_type."""
        if self.copy_type == CopyType.FEED_CARD:
            return self.feed_card
        elif self.copy_type == CopyType.TOPIC_INTRO:
            return self.topic_intro
        elif self.copy_type == CopyType.TREND_CARD:
            return self.trend_card
        elif self.copy_type == CopyType.REPORT_SECTION:
            return self.report_section
        return None


class WriterInput(BaseModel):
    """Input schema for Writer Agent."""

    # Target
    topic_id: int
    copy_type: CopyType

    # Topic information
    topic_title: str
    topic_summary: str | None = None
    board_type: str | None = None
    tags: list[str] = Field(default_factory=list)

    # From Historian
    historian_output: dict[str, Any] | None = None
    history_summary: str | None = None
    first_seen_at: datetime | None = None
    what_is_new_this_time: str | None = None
    historical_status: str | None = None

    # From Analyst
    analyst_output: dict[str, Any] | None = None
    why_it_matters: str | None = None
    system_judgement: str | None = None
    likely_audience: list[str] = Field(default_factory=list)
    follow_up_points: list[str] = Field(default_factory=list)
    trend_stage: str | None = None

    # Representative items
    representative_items: list[dict[str, Any]] = Field(default_factory=list)

    # Metrics
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0

    # Timeline (for context)
    timeline_points: list[dict[str, Any]] = Field(default_factory=list)

    # Additional context
    additional_context: dict[str, Any] = Field(default_factory=dict)
