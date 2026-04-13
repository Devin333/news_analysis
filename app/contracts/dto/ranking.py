"""Ranking DTOs for scoring and ranking topics."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RankingFeatureDTO(BaseModel):
    """Features used for ranking a topic.

    Contains all signals that can influence ranking score.
    """

    topic_id: int

    # Time-based features
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    stale_penalty: float = Field(default=0.0, ge=0.0, le=1.0)

    # Source features
    source_authority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_diversity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trusted_source_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Topic metrics
    topic_heat_score: float = Field(default=0.0, ge=0.0, le=1.0)
    topic_size_score: float = Field(default=0.0, ge=0.0, le=1.0)
    item_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)

    # Trend features
    trend_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trend_signal_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Agent analysis features
    insight_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    analyst_importance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    historian_novelty_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Review features
    review_passed: bool = False
    review_pass_bonus: float = Field(default=0.0, ge=0.0, le=1.0)

    # Board/Homepage features
    board_weight: float = Field(default=1.0, ge=0.0)
    homepage_candidate_score: float = Field(default=0.0, ge=0.0, le=1.0)

    # Metadata
    computed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankingScoreDTO(BaseModel):
    """Final ranking score for a topic."""

    topic_id: int
    final_score: float = Field(default=0.0)
    strategy_name: str = "default"

    # Score breakdown
    component_scores: dict[str, float] = Field(default_factory=dict)

    # Explanation
    explanation: str | None = None
    top_factors: list[str] = Field(default_factory=list)

    # Metadata
    computed_at: datetime | None = None
    context_name: str | None = None


class RankedTopicDTO(BaseModel):
    """A topic with its ranking information."""

    topic_id: int
    rank: int = Field(ge=1)
    score: float

    # Topic basic info
    title: str
    board_type: str
    summary: str | None = None

    # Ranking details
    strategy_name: str = "default"
    features: RankingFeatureDTO | None = None
    score_breakdown: dict[str, float] = Field(default_factory=dict)

    # Metadata
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    item_count: int = 0


class RankingContextDTO(BaseModel):
    """Context for ranking operations."""

    context_name: str  # e.g., "news_feed", "tech_feed", "homepage", "trend"
    board_type: str | None = None
    time_window_hours: int = 24
    max_results: int = 50

    # Filters
    include_unreviewed: bool = False
    min_item_count: int = 1
    min_source_count: int = 1

    # Weights override
    custom_weights: dict[str, float] = Field(default_factory=dict)

    # Metadata
    user_key: str | None = None
    request_id: str | None = None
