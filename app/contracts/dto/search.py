"""Search DTOs for query and result handling."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SearchContentType(StrEnum):
    """Content types for search filtering."""

    TOPIC = "topic"
    ITEM = "item"
    ENTITY = "entity"
    HISTORY = "history"
    ALL = "all"


class SearchMode(StrEnum):
    """Search mode."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SearchQueryDTO(BaseModel):
    """Search query parameters."""

    query: str = Field(..., min_length=1, max_length=500)

    # Filters
    board_filter: list[str] = Field(default_factory=list)
    content_type_filter: list[SearchContentType] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    # Date range
    date_from: datetime | None = None
    date_to: datetime | None = None

    # Search options
    top_k: int = Field(default=20, ge=1, le=100)
    semantic_enabled: bool = True
    mode: SearchMode = SearchMode.HYBRID

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    # Advanced options
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_explanation: bool = False
    highlight_enabled: bool = True

    # Context
    user_key: str | None = None
    request_id: str | None = None


class SearchResultItemDTO(BaseModel):
    """Single search result item."""

    # Identity
    id: int
    content_type: SearchContentType
    score: float = Field(ge=0.0)

    # Content
    title: str
    summary: str | None = None
    excerpt: str | None = None

    # Metadata
    board_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Match info
    matched_by: str | None = None  # keyword, semantic, hybrid
    matched_fields: list[str] = Field(default_factory=list)
    matched_tags: list[str] = Field(default_factory=list)

    # Scores
    keyword_score: float | None = None
    semantic_score: float | None = None

    # Highlights
    highlights: dict[str, list[str]] = Field(default_factory=dict)

    # Additional data
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponseDTO(BaseModel):
    """Search response with results and metadata."""

    # Query info
    query: str
    mode: SearchMode
    total_results: int

    # Results
    results: list[SearchResultItemDTO] = Field(default_factory=list)

    # Pagination
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    # Timing
    search_time_ms: float
    searched_at: datetime

    # Filters applied
    filters_applied: dict[str, Any] = Field(default_factory=dict)

    # Suggestions
    suggestions: list[str] = Field(default_factory=list)
    did_you_mean: str | None = None

    # Debug info
    debug_info: dict[str, Any] | None = None


class SearchSuggestionDTO(BaseModel):
    """Search suggestion/autocomplete item."""

    text: str
    type: str  # query, tag, entity, topic
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchFacetDTO(BaseModel):
    """Search facet for filtering."""

    name: str
    values: list[dict[str, Any]] = Field(default_factory=list)
    # Each value: {"value": "ai", "count": 42, "selected": False}


class SearchExplanationDTO(BaseModel):
    """Explanation for why a result matched."""

    result_id: int
    content_type: SearchContentType
    final_score: float

    # Match details
    keyword_matches: list[dict[str, Any]] = Field(default_factory=list)
    semantic_similarity: float | None = None

    # Score breakdown
    score_components: dict[str, float] = Field(default_factory=dict)

    # Human-readable explanation
    explanation_text: str | None = None
