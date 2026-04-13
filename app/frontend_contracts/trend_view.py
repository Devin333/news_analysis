"""Trend view contracts for frontend display.

Defines the structure of trend data as displayed to users.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TrendSignalView(BaseModel):
    """View model for a trend signal."""

    signal_type: str
    strength: float
    description: str
    evidence: list[str] = Field(default_factory=list)


class TrendTopicView(BaseModel):
    """View model for a topic in trend context."""

    topic_id: int
    title: str
    summary: str | None = None
    trend_stage: str
    trend_score: float
    heat_score: float
    is_emerging: bool = False
    signals: list[TrendSignalView] = Field(default_factory=list)
    watch_points: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    last_updated: datetime | None = None


class TrendCardView(BaseModel):
    """View model for a trend card display.

    Contains all information needed to render a trend card.
    """

    # Core identification
    topic_id: int

    # Display content
    trend_title: str
    trend_summary: str
    signal_summary: str
    stage_label: str

    # Trend indicators
    momentum_indicator: str | None = None
    trend_score: float = 0.0
    heat_score: float = 0.0

    # Signals
    signals: list[TrendSignalView] = Field(default_factory=list)

    # Watch points
    watch_points: list[str] = Field(default_factory=list)

    # Related topics
    related_topics: list[int] = Field(default_factory=list)

    # Visual hints
    trend_direction: str = "stable"  # up, down, stable
    confidence: float = 0.0

    # Timestamps
    detected_at: datetime | None = None
    last_updated: datetime | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendSectionView(BaseModel):
    """View model for a trend section (e.g., 'Emerging', 'Rising')."""

    section_id: str
    section_title: str
    section_description: str | None = None
    trends: list[TrendCardView] = Field(default_factory=list)
    display_style: str = "cards"  # cards, list, compact


class TrendPageView(BaseModel):
    """View model for the trends page.

    Contains multiple sections of trends.
    """

    # Sections
    emerging_trends: list[TrendCardView] = Field(default_factory=list)
    rising_trends: list[TrendCardView] = Field(default_factory=list)
    stable_trends: list[TrendCardView] = Field(default_factory=list)

    # Organized sections
    sections: list[TrendSectionView] = Field(default_factory=list)

    # Summary stats
    total_emerging: int = 0
    total_rising: int = 0
    total_active: int = 0

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    cache_key: str | None = None


class TrendDetailView(BaseModel):
    """Detailed view for a single trend."""

    topic_id: int
    title: str
    summary: str | None = None

    # Trend analysis
    is_emerging: bool = False
    trend_stage: str
    trend_score: float
    confidence: float

    # Signals
    signals: list[TrendSignalView] = Field(default_factory=list)
    signal_summary: str | None = None

    # Why now
    why_now: str | None = None

    # Watch points
    watch_points: list[str] = Field(default_factory=list)

    # Historical context
    first_detected: datetime | None = None
    stage_history: list[dict[str, Any]] = Field(default_factory=list)

    # Related
    related_topics: list[TrendTopicView] = Field(default_factory=list)

    # Recommendations
    recommended_for_homepage: bool = False

    # Metadata
    analyzed_at: datetime | None = None


def build_trend_card_view(
    topic: Any,
    trend_output: dict[str, Any] | None = None,
    writer_copy: dict[str, Any] | None = None,
) -> TrendCardView:
    """Build a TrendCardView from topic and trend data.

    Args:
        topic: Topic data.
        trend_output: TrendHunter output.
        writer_copy: Writer-generated trend card copy.

    Returns:
        TrendCardView.
    """
    # Default values
    trend_title = topic.get("title", "")
    trend_summary = ""
    signal_summary = ""
    stage_label = "stable"
    signals = []
    watch_points = []

    # From trend output
    if trend_output:
        stage_label = trend_output.get("trend_stage", "stable")
        trend_summary = trend_output.get("trend_summary", "")
        signal_summary = trend_output.get("signal_summary", "")
        watch_points = trend_output.get("follow_up_watchpoints", [])

        for sig in trend_output.get("signals", []):
            signals.append(TrendSignalView(
                signal_type=sig.get("signal_type", "unknown"),
                strength=sig.get("strength", 0.0),
                description=sig.get("description", ""),
                evidence=sig.get("evidence", []),
            ))

    # From writer copy (override if available)
    if writer_copy:
        trend_title = writer_copy.get("trend_title", trend_title)
        trend_summary = writer_copy.get("trend_summary", trend_summary)
        signal_summary = writer_copy.get("signal_summary", signal_summary)
        stage_label = writer_copy.get("stage_label", stage_label)
        watch_points = writer_copy.get("watch_points", watch_points)

    return TrendCardView(
        topic_id=topic.get("id", 0),
        trend_title=trend_title,
        trend_summary=trend_summary,
        signal_summary=signal_summary,
        stage_label=stage_label,
        trend_score=float(topic.get("trend_score", 0)),
        heat_score=float(topic.get("heat_score", 0)),
        signals=signals,
        watch_points=watch_points,
        confidence=trend_output.get("confidence", 0.0) if trend_output else 0.0,
    )
