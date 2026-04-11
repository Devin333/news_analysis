"""Normalized item DTOs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.common.enums import BoardType, ContentType


class NormalizedItemDTO(BaseModel):
    """DTO representing normalized content."""

    id: int | None = None
    raw_item_id: int | None = None
    source_id: int
    title: str
    clean_text: str
    excerpt: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    content_type: ContentType = ContentType.ARTICLE
    board_type_candidate: BoardType = BoardType.GENERAL
    quality_score: float = 0.0
    ai_relevance_score: float = 0.0
    canonical_url: str | None = None
    metadata_json: dict[str, Any] = {}
