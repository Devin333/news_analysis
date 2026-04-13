"""Historian Agent output schemas.

Defines the structured output format for the Historian Agent,
which provides historical context and analysis for topics.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HistoricalStatus(StrEnum):
    """Historical status of a topic."""

    NEW = "new"  # First time appearing
    EVOLVING = "evolving"  # Ongoing development
    RECURRING = "recurring"  # Old topic resurfacing
    MILESTONE = "milestone"  # Significant update/release


class TopicStage(StrEnum):
    """Current stage of a topic."""

    EMERGING = "emerging"  # Just starting to gain attention
    ACTIVE = "active"  # Actively being discussed
    STABLE = "stable"  # Established, steady coverage
    DECLINING = "declining"  # Losing attention


class TimelinePoint(BaseModel):
    """A point on the topic timeline."""

    event_time: datetime
    event_type: str
    title: str
    description: str | None = None
    importance: float = 0.5  # 0-1


class SimilarPastTopic(BaseModel):
    """Reference to a similar past topic."""

    topic_id: int
    title: str
    similarity_reason: str
    relevance_score: float = 0.5


class HistorianOutput(BaseModel):
    """Output schema for Historian Agent.

    Contains historical analysis and context for a topic.
    """

    # Core temporal information
    first_seen_at: datetime = Field(
        description="When this topic was first observed"
    )
    last_seen_at: datetime = Field(
        description="Most recent observation of this topic"
    )

    # Historical classification
    historical_status: HistoricalStatus = Field(
        description="Whether this is new, evolving, recurring, or a milestone"
    )

    # Current stage
    current_stage: TopicStage = Field(
        default=TopicStage.EMERGING,
        description="Current lifecycle stage of the topic"
    )

    # Historical summary
    history_summary: str = Field(
        description="Summary of the topic's history and evolution"
    )

    # Timeline
    timeline_points: list[TimelinePoint] = Field(
        default_factory=list,
        description="Key events in the topic's timeline"
    )

    # What's new
    what_is_new_this_time: str = Field(
        description="What's different or new in the current coverage"
    )

    # Similar past topics
    similar_past_topics: list[SimilarPastTopic] = Field(
        default_factory=list,
        description="Similar topics from the past"
    )

    # Important background
    important_background: str | None = Field(
        default=None,
        description="Important background context for understanding this topic"
    )

    # Confidence
    historical_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the historical analysis (0-1)"
    )

    # Evidence
    evidence_sources: list[str] = Field(
        default_factory=list,
        description="Sources used for historical analysis"
    )

    # Metadata
    analysis_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the analysis"
    )


class HistorianInput(BaseModel):
    """Input schema for Historian Agent."""

    # Topic information
    topic_id: int
    topic_title: str
    topic_summary: str | None = None
    board_type: str | None = None

    # Current state
    current_item_count: int = 0
    current_source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0

    # Representative items
    representative_item_title: str | None = None
    representative_item_excerpt: str | None = None
    representative_item_url: str | None = None

    # Historical context
    existing_timeline: list[TimelinePoint] = Field(default_factory=list)
    existing_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    existing_memory: dict[str, Any] | None = None

    # Related context
    related_topic_ids: list[int] = Field(default_factory=list)
    entity_names: list[str] = Field(default_factory=list)

    # Recent items for analysis
    recent_items: list[dict[str, Any]] = Field(default_factory=list)


class HistorianToolResult(BaseModel):
    """Result from a Historian tool call."""

    tool_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
