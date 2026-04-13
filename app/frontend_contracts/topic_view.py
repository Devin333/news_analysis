"""Topic view models for frontend consumption.

Contains enriched topic views with historical context and insights.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimelinePointView(BaseModel):
    """Timeline point for display."""

    event_time: datetime
    event_type: str
    title: str
    description: str | None = None
    importance: float = 0.5


class TopicDetailView(BaseModel):
    """Enriched topic detail view for frontend.

    Includes base topic info plus historical context and insights.
    """

    # Base topic info
    id: int
    title: str
    summary: str | None = None
    board_type: str
    topic_type: str | None = None

    # Metrics
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0

    # Timestamps
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    created_at: datetime | None = None

    # Representative item
    representative_item_id: int | None = None
    representative_item_title: str | None = None
    representative_item_url: str | None = None

    # Historical context (from Historian)
    history_summary: str | None = Field(
        default=None,
        description="Summary of the topic's history and evolution"
    )
    historical_status: str | None = Field(
        default=None,
        description="new, evolving, recurring, or milestone"
    )
    current_stage: str | None = Field(
        default=None,
        description="emerging, active, stable, or declining"
    )
    what_is_new_this_time: str | None = Field(
        default=None,
        description="What's different in the current coverage"
    )
    timeline_points: list[TimelinePointView] = Field(
        default_factory=list,
        description="Key events in the topic's timeline"
    )
    historical_confidence: float | None = Field(
        default=None,
        description="Confidence in historical analysis (0-1)"
    )

    # Insights (from Analyst - to be added in Day 82)
    why_it_matters: str | None = Field(
        default=None,
        description="Why this topic is important"
    )
    system_judgement: str | None = Field(
        default=None,
        description="System's assessment of the topic"
    )
    likely_audience: list[str] = Field(
        default_factory=list,
        description="Who would be interested in this topic"
    )
    follow_up_points: list[str] = Field(
        default_factory=list,
        description="Points to follow up on"
    )
    trend_stage: str | None = Field(
        default=None,
        description="Current trend stage"
    )

    # Writer-generated content
    headline: str | None = Field(
        default=None,
        description="Writer-generated headline"
    )
    intro: str | None = Field(
        default=None,
        description="Writer-generated introduction"
    )
    key_takeaways: list[str] = Field(
        default_factory=list,
        description="Writer-generated key takeaways"
    )
    background_context: str | None = Field(
        default=None,
        description="Writer-generated background context"
    )
    related_reading_hints: list[str] = Field(
        default_factory=list,
        description="Writer-generated related reading suggestions"
    )

    # Tags
    tags: list[str] = Field(default_factory=list)

    # Metadata
    has_historical_context: bool = False
    has_insights: bool = False
    has_writer_copy: bool = False
    last_enriched_at: datetime | None = None
    review_status: str | None = Field(
        default=None,
        description="Review status: approved, revise, reject, pending"
    )


class TopicListItemView(BaseModel):
    """Lightweight topic view for list display."""

    id: int
    title: str
    summary: str | None = None
    board_type: str
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0
    trend_score: float = 0.0
    last_seen_at: datetime | None = None
    historical_status: str | None = None
    tags: list[str] = Field(default_factory=list)


class TopicHistorianOutputView(BaseModel):
    """View for historian output API response."""

    topic_id: int
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    historical_status: str | None = None
    current_stage: str | None = None
    history_summary: str | None = None
    what_is_new_this_time: str | None = None
    timeline_points: list[TimelinePointView] = Field(default_factory=list)
    similar_past_topics: list[int] = Field(default_factory=list)
    important_background: str | None = None
    historical_confidence: float | None = None
    evidence_sources: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


def build_topic_detail_view(
    topic: Any,
    historian_output: dict[str, Any] | None = None,
    insight_output: dict[str, Any] | None = None,
    representative_item: Any | None = None,
    tags: list[str] | None = None,
) -> TopicDetailView:
    """Build a TopicDetailView from topic and optional enrichments.

    Args:
        topic: TopicReadDTO or similar.
        historian_output: Optional historian output dict.
        insight_output: Optional analyst insight dict.
        representative_item: Optional representative item.
        tags: Optional list of tag names.

    Returns:
        TopicDetailView with all available data.
    """
    # Build timeline points from historian output
    timeline_points = []
    if historian_output and historian_output.get("timeline_points"):
        for tp in historian_output["timeline_points"][:10]:
            timeline_points.append(TimelinePointView(
                event_time=tp.get("event_time") or datetime.utcnow(),
                event_type=tp.get("event_type", "unknown"),
                title=tp.get("title", ""),
                description=tp.get("description"),
                importance=tp.get("importance", 0.5),
            ))

    view = TopicDetailView(
        id=topic.id,
        title=topic.title,
        summary=topic.summary,
        board_type=str(topic.board_type),
        topic_type=getattr(topic, "topic_type", None),
        item_count=topic.item_count,
        source_count=topic.source_count,
        heat_score=float(topic.heat_score),
        trend_score=float(topic.trend_score),
        first_seen_at=topic.first_seen_at,
        last_seen_at=topic.last_seen_at,
        created_at=getattr(topic, "created_at", None),
        representative_item_id=topic.representative_item_id,
        tags=tags or [],
    )

    # Add representative item info
    if representative_item:
        view.representative_item_title = representative_item.title
        view.representative_item_url = representative_item.url

    # Add historian output
    if historian_output:
        view.history_summary = historian_output.get("history_summary")
        view.historical_status = historian_output.get("historical_status")
        view.current_stage = historian_output.get("current_stage")
        view.what_is_new_this_time = historian_output.get("what_is_new_this_time")
        view.timeline_points = timeline_points
        view.historical_confidence = historian_output.get("historical_confidence")
        view.has_historical_context = True
        view.last_enriched_at = datetime.utcnow()

    # Add analyst insight
    if insight_output:
        view.why_it_matters = insight_output.get("why_it_matters")
        view.system_judgement = insight_output.get("system_judgement")
        view.likely_audience = insight_output.get("likely_audience", [])
        # Convert follow_up_points to simple strings
        follow_ups = insight_output.get("follow_up_points", [])
        view.follow_up_points = [
            fp.get("topic", str(fp)) if isinstance(fp, dict) else str(fp)
            for fp in follow_ups
        ]
        view.trend_stage = insight_output.get("trend_stage")
        view.has_insights = True
        view.last_enriched_at = datetime.utcnow()

    return view


class TopicInsightView(BaseModel):
    """View for analyst insight API response."""

    topic_id: int
    why_it_matters: str | None = None
    system_judgement: str | None = None
    likely_audience: list[str] = Field(default_factory=list)
    follow_up_points: list[dict[str, Any]] = Field(default_factory=list)
    trend_stage: str | None = None
    trend_momentum: float | None = None
    confidence: float | None = None
    evidence_summary: str | None = None
    key_signals: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None
