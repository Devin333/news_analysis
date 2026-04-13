"""Analyst Agent output schemas.

Defines the structured output format for the Analyst Agent,
which provides value judgement and analysis for topics.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TrendStage(StrEnum):
    """Trend stage of a topic."""

    EARLY_SIGNAL = "early_signal"  # Early indicator, not yet mainstream
    RISING = "rising"  # Gaining momentum
    PEAK = "peak"  # At peak attention
    PLATEAU = "plateau"  # Stable, sustained interest
    DECLINING = "declining"  # Losing attention
    NOISE = "noise"  # Likely noise, not a real trend


class AudienceType(StrEnum):
    """Types of potential audience."""

    DEVELOPERS = "developers"
    RESEARCHERS = "researchers"
    BUSINESS_LEADERS = "business_leaders"
    INVESTORS = "investors"
    GENERAL_TECH = "general_tech"
    ENTERPRISE = "enterprise"
    STARTUPS = "startups"
    STUDENTS = "students"


class FollowUpPoint(BaseModel):
    """A point to follow up on."""

    topic: str
    reason: str
    priority: float = 0.5  # 0-1


class AnalystOutput(BaseModel):
    """Output schema for Analyst Agent.

    Contains value analysis and judgement for a topic.
    """

    # Core judgement
    why_it_matters: str = Field(
        description="Why this topic is important and worth attention"
    )
    system_judgement: str = Field(
        description="System's overall assessment of the topic"
    )

    # Audience analysis
    likely_audience: list[str] = Field(
        default_factory=list,
        description="Who would be most interested in this topic"
    )
    audience_relevance: dict[str, float] = Field(
        default_factory=dict,
        description="Relevance score (0-1) for each audience type"
    )

    # Follow-up recommendations
    follow_up_points: list[FollowUpPoint] = Field(
        default_factory=list,
        description="Points worth following up on"
    )

    # Trend analysis
    trend_stage: TrendStage = Field(
        default=TrendStage.EARLY_SIGNAL,
        description="Current stage in the trend lifecycle"
    )
    trend_momentum: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Trend momentum (-1 to 1, negative = declining)"
    )

    # Confidence
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the analysis (0-1)"
    )

    # Evidence
    evidence_summary: str | None = Field(
        default=None,
        description="Summary of evidence supporting the analysis"
    )
    key_signals: list[str] = Field(
        default_factory=list,
        description="Key signals that informed the analysis"
    )

    # Metadata
    analysis_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the analysis"
    )


class AnalystInput(BaseModel):
    """Input schema for Analyst Agent."""

    # Topic information
    topic_id: int
    topic_title: str
    topic_summary: str | None = None
    board_type: str | None = None

    # Current metrics
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0

    # Representative item
    representative_item_title: str | None = None
    representative_item_excerpt: str | None = None

    # Tags
    tags: list[str] = Field(default_factory=list)

    # Historian output (if available)
    historical_status: str | None = None
    current_stage: str | None = None
    history_summary: str | None = None
    what_is_new_this_time: str | None = None

    # Recent items for analysis
    recent_items: list[dict[str, Any]] = Field(default_factory=list)

    # Entity context
    entity_names: list[str] = Field(default_factory=list)

    # Recent judgements
    recent_judgements: list[dict[str, Any]] = Field(default_factory=list)


class AnalystToolResult(BaseModel):
    """Result from an Analyst tool call."""

    tool_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
