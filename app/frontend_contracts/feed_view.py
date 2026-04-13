"""Feed view contracts for frontend display.

Defines the structure of feed items as displayed to users.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FeedItemView(BaseModel):
    """View model for a single feed item.

    Contains all information needed to render a feed card.
    """

    # Core identification
    topic_id: int
    item_id: int | None = None

    # Display content (from Writer)
    title: str
    short_summary: str
    why_it_matters_short: str | None = None

    # Classification
    board_type: str | None = None
    display_tags: list[str] = Field(default_factory=list)
    content_type: str | None = None

    # Audience and relevance
    audience_hint: str | None = None
    relevance_score: float | None = None

    # Trend information
    trend_stage: str | None = None
    historical_status: str | None = None
    is_emerging: bool = False

    # Metrics
    item_count: int = 0
    source_count: int = 0
    heat_score: float = 0.0

    # Timestamps
    first_seen_at: datetime | None = None
    last_updated_at: datetime | None = None

    # Source information
    primary_source: str | None = None
    source_url: str | None = None

    # Visual hints
    thumbnail_url: str | None = None
    icon_type: str | None = None

    # Interaction hints
    has_timeline: bool = False
    has_related_topics: bool = False

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedListView(BaseModel):
    """View model for a feed list.

    Contains a list of feed items with pagination info.
    """

    items: list[FeedItemView] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False

    # Filter state
    board_filter: str | None = None
    tag_filter: list[str] = Field(default_factory=list)
    sort_by: str = "relevance"

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_key: str | None = None


class FeedSectionView(BaseModel):
    """View model for a feed section (e.g., 'Trending', 'New').

    Groups feed items by category.
    """

    section_id: str
    section_title: str
    section_description: str | None = None
    items: list[FeedItemView] = Field(default_factory=list)
    show_more_link: str | None = None
    display_style: str = "list"  # list, grid, carousel


class HomeFeedView(BaseModel):
    """View model for the home feed page.

    Contains multiple sections of feed items.
    """

    sections: list[FeedSectionView] = Field(default_factory=list)
    featured_topic: FeedItemView | None = None
    trending_tags: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
