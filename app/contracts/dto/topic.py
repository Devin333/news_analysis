"""Topic related DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.common.enums import BoardType


class TopicCreateDTO(BaseModel):
    """DTO for creating a new topic."""

    board_type: BoardType = BoardType.GENERAL
    topic_type: str = "auto"
    title: str = Field(min_length=1, max_length=512)
    summary: str | None = None
    representative_item_id: int | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class TopicReadDTO(BaseModel):
    """DTO for reading topic details."""

    id: int
    board_type: BoardType
    topic_type: str
    title: str
    summary: str | None
    representative_item_id: int | None
    first_seen_at: datetime
    last_seen_at: datetime
    item_count: int
    source_count: int
    heat_score: float
    trend_score: float
    status: str
    metadata_json: dict[str, Any]


class TopicSummaryDTO(BaseModel):
    """DTO for topic summary (lightweight view)."""

    id: int
    title: str
    board_type: BoardType
    item_count: int
    source_count: int
    heat_score: float
    last_seen_at: datetime


class TopicCandidateDTO(BaseModel):
    """DTO for a candidate topic during merge evaluation."""

    topic_id: int
    title: str
    board_type: BoardType
    item_count: int
    last_seen_at: datetime
    similarity_score: float = 0.0
    match_reasons: list[str] = Field(default_factory=list)


class TopicCandidateScoreDTO(BaseModel):
    """DTO for scored topic candidate."""

    topic_id: int
    title: str
    total_score: float
    title_similarity: float = 0.0
    tag_overlap: float = 0.0
    recency_score: float = 0.0
    source_similarity: float = 0.0
    embedding_similarity: float = 0.0
    should_merge: bool = False
    confidence: float = 0.0


class TopicItemLinkDTO(BaseModel):
    """DTO for topic-item relationship."""

    topic_id: int
    item_id: int
    link_reason: str | None = None
    created_at: datetime | None = None


class TopicMetricsUpdateDTO(BaseModel):
    """DTO for updating topic metrics."""

    item_count: int | None = None
    source_count: int | None = None
    heat_score: float | None = None
    trend_score: float | None = None
    last_seen_at: datetime | None = None
