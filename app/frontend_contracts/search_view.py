"""Search view contracts for frontend."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchResultView(BaseModel):
    """Search result for frontend display."""

    id: int
    type: str  # topic, item, entity, history
    score: float

    # Display fields
    title: str
    summary: str | None = None
    excerpt: str | None = None

    # Metadata
    board_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    date: str | None = None  # ISO format

    # Match info
    match_type: str | None = None  # keyword, semantic, hybrid
    highlights: dict[str, list[str]] = Field(default_factory=dict)

    # Additional info
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponseView(BaseModel):
    """Search response for frontend."""

    query: str
    total: int
    results: list[SearchResultView] = Field(default_factory=list)

    # Pagination
    page: int
    page_size: int
    total_pages: int
    has_more: bool

    # Timing
    search_time_ms: float

    # Suggestions
    suggestions: list[str] = Field(default_factory=list)
    did_you_mean: str | None = None

    # Facets for filtering
    facets: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class SearchSuggestionView(BaseModel):
    """Search suggestion for autocomplete."""

    text: str
    type: str  # query, tag, entity, topic
    count: int | None = None


class SearchFiltersView(BaseModel):
    """Available search filters."""

    boards: list[dict[str, Any]] = Field(default_factory=list)
    content_types: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[dict[str, Any]] = Field(default_factory=list)
    date_ranges: list[dict[str, Any]] = Field(default_factory=list)


def to_search_result_view(result: Any) -> SearchResultView:
    """Convert search result DTO to view.

    Args:
        result: SearchResultItemDTO

    Returns:
        SearchResultView for frontend
    """
    return SearchResultView(
        id=result.id,
        type=result.content_type.value,
        score=result.score,
        title=result.title,
        summary=result.summary,
        excerpt=result.excerpt,
        board_type=result.board_type,
        tags=result.tags,
        date=result.created_at.isoformat() if result.created_at else None,
        match_type=result.matched_by,
        highlights=result.highlights,
        metadata=result.metadata,
    )


def to_search_response_view(response: Any) -> SearchResponseView:
    """Convert search response DTO to view.

    Args:
        response: SearchResponseDTO

    Returns:
        SearchResponseView for frontend
    """
    return SearchResponseView(
        query=response.query,
        total=response.total_results,
        results=[to_search_result_view(r) for r in response.results],
        page=response.page,
        page_size=response.page_size,
        total_pages=response.total_pages,
        has_more=response.has_next,
        search_time_ms=response.search_time_ms,
        suggestions=response.suggestions,
        did_you_mean=response.did_you_mean,
    )
