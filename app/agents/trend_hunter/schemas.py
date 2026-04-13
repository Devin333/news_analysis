"""TrendHunter Agent output schemas.

Defines the structured output formats for the TrendHunter Agent.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TrendStage(StrEnum):
    """Stage of a trend."""

    EMERGING = "emerging"
    GROWING = "growing"
    PEAK = "peak"
    STABLE = "stable"
    DECLINING = "declining"


class SignalType(StrEnum):
    """Type of trend signal."""

    GROWTH = "growth"  # Item count growth
    DIVERSITY = "diversity"  # Source diversity increase
    RECENCY = "recency"  # Recent activity spike
    RELEASE = "release"  # New release/version
    DISCUSSION = "discussion"  # Discussion spike
    ENTITY_ACTIVITY = "entity_activity"  # Related entity activity
    REPEATED = "repeated"  # Repeated appearance


class TrendSignal(BaseModel):
    """A detected trend signal."""

    signal_type: str
    strength: float = Field(ge=0.0, le=1.0)
    description: str
    evidence: list[str] = Field(default_factory=list)


class TrendHunterOutput(BaseModel):
    """Output schema for TrendHunter Agent."""

    # Core assessment
    is_emerging: bool = Field(
        description="Whether this is an emerging trend"
    )
    trend_stage: TrendStage = Field(
        description="Current stage of the trend"
    )

    # Summary
    trend_summary: str = Field(
        description="Summary of the trend (2-3 sentences)"
    )
    signal_summary: str = Field(
        description="Summary of detected signals"
    )

    # Why now
    why_now: str = Field(
        description="Why this trend is happening now"
    )

    # Signals
    signals: list[TrendSignal] = Field(
        default_factory=list,
        description="Detected trend signals"
    )

    # Recommendations
    recommended_for_homepage: bool = Field(
        default=False,
        description="Whether to feature on homepage"
    )
    follow_up_watchpoints: list[str] = Field(
        default_factory=list,
        description="What to watch for next"
    )

    # Confidence
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence in the assessment"
    )

    # Metadata
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendHunterInput(BaseModel):
    """Input schema for TrendHunter Agent."""

    # Topic info
    topic_id: int
    topic_title: str
    topic_summary: str | None = None
    board_type: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Metrics
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0

    # Growth metrics
    item_count_7d: int = 0
    item_count_30d: int = 0
    source_count_7d: int = 0
    source_count_30d: int = 0
    growth_rate_7d: float = 0.0
    growth_rate_30d: float = 0.0

    # Recency
    last_item_at: datetime | None = None
    items_last_24h: int = 0
    items_last_7d: int = 0

    # Source diversity
    unique_sources_7d: int = 0
    source_diversity_score: float = 0.0

    # From Historian
    historian_output: dict[str, Any] | None = None
    historical_status: str | None = None
    first_seen_at: datetime | None = None

    # From Analyst
    analyst_output: dict[str, Any] | None = None
    why_it_matters: str | None = None
    system_judgement: str | None = None

    # Related signals
    has_recent_release: bool = False
    has_discussion_spike: bool = False
    related_entity_activity: list[str] = Field(default_factory=list)

    # Previous trend assessment
    previous_trend_stage: str | None = None
    previous_assessment_at: datetime | None = None
