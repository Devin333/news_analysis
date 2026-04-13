"""Search protocols for search engine implementations."""

from typing import Protocol, runtime_checkable

from app.contracts.dto.search import (
    SearchQueryDTO,
    SearchResponseDTO,
    SearchResultItemDTO,
    SearchSuggestionDTO,
)


@runtime_checkable
class SearchEngineProtocol(Protocol):
    """Protocol for search engine implementations.

    Supports keyword, semantic, and hybrid search.
    """

    async def search(
        self,
        query: SearchQueryDTO,
    ) -> SearchResponseDTO:
        """Execute a search query.

        Args:
            query: Search query parameters

        Returns:
            SearchResponseDTO with results
        """
        ...

    async def search_topics(
        self,
        query: SearchQueryDTO,
    ) -> SearchResponseDTO:
        """Search topics specifically.

        Args:
            query: Search query parameters

        Returns:
            SearchResponseDTO with topic results
        """
        ...

    async def search_entities(
        self,
        query: SearchQueryDTO,
    ) -> SearchResponseDTO:
        """Search entities specifically.

        Args:
            query: Search query parameters

        Returns:
            SearchResponseDTO with entity results
        """
        ...

    async def search_history(
        self,
        query: SearchQueryDTO,
    ) -> SearchResponseDTO:
        """Search historical cases.

        Args:
            query: Search query parameters

        Returns:
            SearchResponseDTO with history results
        """
        ...


@runtime_checkable
class KeywordSearchProtocol(Protocol):
    """Protocol for keyword-based search."""

    async def search(
        self,
        query: str,
        *,
        filters: dict | None = None,
        limit: int = 20,
    ) -> list[SearchResultItemDTO]:
        """Execute keyword search.

        Args:
            query: Search query string
            filters: Optional filters
            limit: Maximum results

        Returns:
            List of search results
        """
        ...


@runtime_checkable
class SemanticSearchProtocol(Protocol):
    """Protocol for semantic/vector search."""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[SearchResultItemDTO]:
        """Execute semantic search.

        Args:
            query: Search query string
            top_k: Number of results
            min_score: Minimum similarity score

        Returns:
            List of search results
        """
        ...

    async def get_similar(
        self,
        item_id: int,
        content_type: str,
        *,
        top_k: int = 10,
    ) -> list[SearchResultItemDTO]:
        """Find similar items.

        Args:
            item_id: Source item ID
            content_type: Content type
            top_k: Number of results

        Returns:
            List of similar items
        """
        ...


@runtime_checkable
class SearchSuggestionProtocol(Protocol):
    """Protocol for search suggestions/autocomplete."""

    async def suggest(
        self,
        prefix: str,
        *,
        limit: int = 10,
    ) -> list[SearchSuggestionDTO]:
        """Get search suggestions.

        Args:
            prefix: Query prefix
            limit: Maximum suggestions

        Returns:
            List of suggestions
        """
        ...

    async def get_popular_queries(
        self,
        *,
        limit: int = 10,
    ) -> list[str]:
        """Get popular search queries.

        Args:
            limit: Maximum queries

        Returns:
            List of popular queries
        """
        ...


@runtime_checkable
class SearchRankerProtocol(Protocol):
    """Protocol for search result ranking."""

    def rank_results(
        self,
        results: list[SearchResultItemDTO],
        query: SearchQueryDTO,
    ) -> list[SearchResultItemDTO]:
        """Rank search results.

        Args:
            results: Unranked results
            query: Original query

        Returns:
            Ranked results
        """
        ...

    def merge_results(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
        *,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
    ) -> list[SearchResultItemDTO]:
        """Merge keyword and semantic results.

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results
            keyword_weight: Weight for keyword scores
            semantic_weight: Weight for semantic scores

        Returns:
            Merged and ranked results
        """
        ...
