"""Tag related DTOs."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TagType(StrEnum):
    """Tag type classification."""

    COMPANY = "company"
    MODEL = "model"
    FRAMEWORK = "framework"
    TASK = "task"
    METHOD = "method"
    SOURCE = "source"
    BOARD = "board"
    CONTENT_TYPE = "content_type"
    TECHNOLOGY_DOMAIN = "technology_domain"


class TagCreateDTO(BaseModel):
    """DTO for creating a new tag."""

    name: str = Field(min_length=1, max_length=128)
    tag_type: TagType
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    parent_tag_id: int | None = None


class TagReadDTO(BaseModel):
    """DTO for reading tag details."""

    id: int
    name: str
    normalized_name: str
    tag_type: TagType
    aliases: list[str]
    description: str | None
    parent_tag_id: int | None
    created_at: datetime


class TagSummaryDTO(BaseModel):
    """DTO for tag summary (lightweight view)."""

    id: int
    name: str
    tag_type: TagType


class ItemTagDTO(BaseModel):
    """DTO for item-tag relationship."""

    item_id: int
    tag_id: int
    tag_name: str
    tag_type: TagType
    confidence: float = 1.0
    source: str = "rule"


class TopicTagDTO(BaseModel):
    """DTO for topic-tag relationship."""

    topic_id: int
    tag_id: int
    tag_name: str
    tag_type: TagType
    confidence: float = 1.0
    item_count: int = 1
    source: str = "aggregated"


class TagMatchDTO(BaseModel):
    """DTO for a tag match result."""

    tag_id: int
    tag_name: str
    tag_type: TagType
    confidence: float
    matched_text: str | None = None
    match_source: str = "rule"  # rule, alias, embedding


class TaggingResultDTO(BaseModel):
    """DTO for tagging operation result."""

    item_id: int | None = None
    topic_id: int | None = None
    tags: list[TagMatchDTO] = Field(default_factory=list)
    processing_time_ms: float = 0.0
