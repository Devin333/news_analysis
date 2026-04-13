"""Search service for unified search operations."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
import time

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import (
    SearchContentType,
    SearchMode,
    SearchQueryDTO,
    SearchResponseDTO,
    SearchResultItemDTO,
)
from app.contracts.protocols.search import (
    KeywordSearchProtocol,
    SearchEngineProtocol,
    SearchRankerProtocol,
    SemanticSearchProtocol,
)

if TYPE_CHECKING:
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class SearchService(SearchEngineProtocol):
    """Unified search service.

    Coordinates keyword and semantic search with ranking.
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
        keyword_search: KeywordSearchProtocol | None = None,
        semantic_search: SemanticSearchProtocol | None = None,
        ranker: SearchRankerProtocol | None = None,
    ) -> None:
        """Initialize search service.

        Args:
            uow: Unit of work for database access
            keyword_search: Keyword search implementation
            semantic_search: Semantic search implementation
            ranker: Result ranker
        """
        self._uow = uow
        self._keyword_search = keyword_search
        self._semantic_search = semantic_search
        self._ranker = ranker

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
        start_time = time.time()

        results: list[SearchResultItemDTO] = []

        if query.mode == SearchMode.KEYWORD:
            results = await self._keyword_search_only(query)
        elif query.mode == SearchMode.SEMANTIC:
            results = await self._semantic_search_only(query)
        else:  # HYBRID
            results = await self._hybrid_search(query)

        # Apply content type filter
        if query.content_type_filter:
            results = [
                r for r in results
                if r.content_type in query.content_type_filter
            ]

        # Apply ranking
        if self._ranker:
            results = self._ranker.rank_results(results, query)

        # Apply pagination
        total_results = len(results)
        start_idx = (query.page - 1) * query.page_size
        end_idx = start_idx + query.page_size
        page_results = results[start_idx:end_idx]

        search_time_ms = (time.time() - start_time) * 1000
        total_pages = (total_results + query.page_size - 1) // query.page_size

        return SearchResponseDTO(
            query=query.query,
            mode=query.mode,
            total_results=total_results,
            results=page_results,
            page=query.page,
            page_size=query.page_size,
            total_pages=total_pages,
            has_next=query.page < total_pages,
            has_prev=query.page > 1,
            search_time_ms=search_time_ms,
            searched_at=datetime.now(timezone.utc),
            filters_applied={
                "board_filter": query.board_filter,
                "content_type_filter": [ct.value for ct in query.content_type_filter],
                "tags": query.tags,
                "date_from": query.date_from.isoformat() if query.date_from else None,
                "date_to": query.date_to.isoformat() if query.date_to else None,
            },
        )

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
        # Force content type to topic
        query.content_type_filter = [SearchContentType.TOPIC]
        return await self.search(query)

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
        query.content_type_filter = [SearchContentType.ENTITY]
        return await self.search(query)

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
        query.content_type_filter = [SearchContentType.HISTORY]
        return await self.search(query)

    async def _keyword_search_only(
        self,
        query: SearchQueryDTO,
    ) -> list[SearchResultItemDTO]:
        """Execute keyword-only search.

        Args:
            query: Search query

        Returns:
            List of results
        """
        if not self._keyword_search:
            return []

        filters = self._build_filters(query)
        results = await self._keyword_search.search(
            query.query,
            filters=filters,
            limit=query.top_k,
        )

        for r in results:
            r.matched_by = "keyword"

        return results

    async def _semantic_search_only(
        self,
        query: SearchQueryDTO,
    ) -> list[SearchResultItemDTO]:
        """Execute semantic-only search.

        Args:
            query: Search query

        Returns:
            List of results
        """
        if not self._semantic_search:
            return []

        results = await self._semantic_search.search(
            query.query,
            top_k=query.top_k,
            min_score=query.min_score,
        )

        for r in results:
            r.matched_by = "semantic"

        return results

    async def _hybrid_search(
        self,
        query: SearchQueryDTO,
    ) -> list[SearchResultItemDTO]:
        """Execute hybrid search combining keyword and semantic.

        Args:
            query: Search query

        Returns:
            Merged and ranked results
        """
        keyword_results: list[SearchResultItemDTO] = []
        semantic_results: list[SearchResultItemDTO] = []

        # Execute both searches
        if self._keyword_search:
            filters = self._build_filters(query)
            keyword_results = await self._keyword_search.search(
                query.query,
                filters=filters,
                limit=query.top_k,
            )
            for r in keyword_results:
                r.matched_by = "keyword"
                r.keyword_score = r.score

        if self._semantic_search and query.semantic_enabled:
            semantic_results = await self._semantic_search.search(
                query.query,
                top_k=query.top_k,
                min_score=query.min_score,
            )
            for r in semantic_results:
                r.matched_by = "semantic"
                r.semantic_score = r.score

        # Merge results
        if self._ranker:
            return self._ranker.merge_results(
                keyword_results,
                semantic_results,
                keyword_weight=0.5,
                semantic_weight=0.5,
            )

        # Simple merge without ranker
        return self._simple_merge(keyword_results, semantic_results)

    def _simple_merge(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
    ) -> list[SearchResultItemDTO]:
        """Simple merge of keyword and semantic results.

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results

        Returns:
            Merged results
        """
        seen_ids: set[tuple[int, str]] = set()
        merged: list[SearchResultItemDTO] = []

        # Add keyword results first
        for r in keyword_results:
            key = (r.id, r.content_type.value)
            if key not in seen_ids:
                seen_ids.add(key)
                merged.append(r)

        # Add semantic results
        for r in semantic_results:
            key = (r.id, r.content_type.value)
            if key not in seen_ids:
                seen_ids.add(key)
                merged.append(r)
            else:
                # Update existing with semantic score
                for m in merged:
                    if m.id == r.id and m.content_type == r.content_type:
                        m.semantic_score = r.score
                        m.matched_by = "hybrid"
                        # Boost score for hybrid match
                        m.score = (m.score + r.score) / 2 * 1.2
                        break

        # Sort by score
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged

    def _build_filters(self, query: SearchQueryDTO) -> dict[str, Any]:
        """Build filters dict from query.

        Args:
            query: Search query

        Returns:
            Filters dict
        """
        filters: dict[str, Any] = {}

        if query.board_filter:
            filters["board_type"] = query.board_filter

        if query.tags:
            filters["tags"] = query.tags

        if query.date_from:
            filters["date_from"] = query.date_from

        if query.date_to:
            filters["date_to"] = query.date_to

        return filters

    async def get_similar_topics(
        self,
        topic_id: int,
        *,
        top_k: int = 10,
    ) -> list[SearchResultItemDTO]:
        """Find topics similar to a given topic.

        Args:
            topic_id: Source topic ID
            top_k: Number of results

        Returns:
            List of similar topics
        """
        if not self._semantic_search:
            return []

        return await self._semantic_search.get_similar(
            topic_id,
            "topic",
            top_k=top_k,
        )

    async def get_similar_entities(
        self,
        entity_id: int,
        *,
        top_k: int = 10,
    ) -> list[SearchResultItemDTO]:
        """Find entities similar to a given entity.

        Args:
            entity_id: Source entity ID
            top_k: Number of results

        Returns:
            List of similar entities
        """
        if not self._semantic_search:
            return []

        return await self._semantic_search.get_similar(
            entity_id,
            "entity",
            top_k=top_k,
        )
