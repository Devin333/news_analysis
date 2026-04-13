"""Hybrid search combining keyword and semantic search."""

from datetime import datetime, timezone
import time
from typing import TYPE_CHECKING, Any

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
    SearchRankerProtocol,
    SemanticSearchProtocol,
)
from app.search.policies import SearchPolicies, SearchPolicyConfig, SearchPolicyMode
from app.search.semantic_result_merger import SemanticResultMerger

if TYPE_CHECKING:
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class HybridSearch:
    """Hybrid search combining keyword and semantic approaches.

    Supports multiple merge strategies and configurable policies.
    """

    def __init__(
        self,
        keyword_search: KeywordSearchProtocol | None = None,
        semantic_search: SemanticSearchProtocol | None = None,
        ranker: SearchRankerProtocol | None = None,
    ) -> None:
        """Initialize hybrid search.

        Args:
            keyword_search: Keyword search implementation
            semantic_search: Semantic search implementation
            ranker: Optional result ranker
        """
        self._keyword_search = keyword_search
        self._semantic_search = semantic_search
        self._ranker = ranker
        self._merger = SemanticResultMerger()

    async def search(
        self,
        query: SearchQueryDTO,
        *,
        policy: SearchPolicyConfig | None = None,
    ) -> SearchResponseDTO:
        """Execute hybrid search.

        Args:
            query: Search query
            policy: Optional search policy

        Returns:
            SearchResponseDTO with results
        """
        start_time = time.time()

        # Get policy
        if policy is None:
            policy = SearchPolicies.user_search()

        # Execute searches based on policy
        keyword_results: list[SearchResultItemDTO] = []
        semantic_results: list[SearchResultItemDTO] = []

        if policy.keyword_enabled and self._keyword_search:
            keyword_results = await self._execute_keyword_search(query, policy)

        if policy.semantic_enabled and self._semantic_search:
            semantic_results = await self._execute_semantic_search(query, policy)

        # Merge results
        merged = self._merge_results(
            keyword_results,
            semantic_results,
            policy,
        )

        # Apply content type filter
        if query.content_type_filter:
            merged = [
                r for r in merged
                if r.content_type in query.content_type_filter
            ]

        # Apply min score filter
        if policy.min_score > 0:
            merged = [r for r in merged if r.score >= policy.min_score]

        # Apply ranking
        if self._ranker:
            merged = self._ranker.rank_results(merged, query)

        # Limit results
        total_results = len(merged)
        merged = merged[:policy.max_results]

        # Apply pagination
        start_idx = (query.page - 1) * query.page_size
        end_idx = start_idx + query.page_size
        page_results = merged[start_idx:end_idx]

        search_time_ms = (time.time() - start_time) * 1000
        total_pages = (total_results + query.page_size - 1) // query.page_size

        return SearchResponseDTO(
            query=query.query,
            mode=SearchMode.HYBRID,
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
                "policy_mode": policy.mode.value,
            },
            debug_info={
                "keyword_count": len(keyword_results),
                "semantic_count": len(semantic_results),
                "merge_strategy": policy.merge_strategy,
            } if query.include_explanation else None,
        )

    async def _execute_keyword_search(
        self,
        query: SearchQueryDTO,
        policy: SearchPolicyConfig,
    ) -> list[SearchResultItemDTO]:
        """Execute keyword search.

        Args:
            query: Search query
            policy: Search policy

        Returns:
            Keyword search results
        """
        if not self._keyword_search:
            return []

        try:
            filters = self._build_filters(query)
            results = await self._keyword_search.search(
                query.query,
                filters=filters,
                limit=policy.max_results * 2,  # Get more for merging
            )

            for r in results:
                r.matched_by = "keyword"
                r.keyword_score = r.score

            return results

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    async def _execute_semantic_search(
        self,
        query: SearchQueryDTO,
        policy: SearchPolicyConfig,
    ) -> list[SearchResultItemDTO]:
        """Execute semantic search.

        Args:
            query: Search query
            policy: Search policy

        Returns:
            Semantic search results
        """
        if not self._semantic_search:
            return []

        try:
            results = await self._semantic_search.search(
                query.query,
                top_k=policy.max_results * 2,
                min_score=policy.min_score,
            )

            for r in results:
                r.matched_by = "semantic"
                r.semantic_score = r.score

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _merge_results(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
        policy: SearchPolicyConfig,
    ) -> list[SearchResultItemDTO]:
        """Merge keyword and semantic results.

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results
            policy: Search policy

        Returns:
            Merged results
        """
        if not keyword_results and not semantic_results:
            return []

        if not keyword_results:
            return semantic_results

        if not semantic_results:
            return keyword_results

        # Update merger weights
        self._merger._keyword_weight = policy.keyword_weight
        self._merger._semantic_weight = policy.semantic_weight

        # Merge based on strategy
        if policy.merge_strategy == "rrf":
            merged = self._merger.merge_rrf(keyword_results, semantic_results)
        elif policy.merge_strategy == "interleaved":
            merged = self._merger.merge_interleaved(keyword_results, semantic_results)
        else:  # weighted
            merged = self._merger.merge_weighted(keyword_results, semantic_results)

        # Boost hybrid matches
        if policy.boost_hybrid:
            merged = self._merger.boost_hybrid_matches(
                merged, policy.hybrid_boost_factor
            )

        # Normalize scores
        merged = self._merger.normalize_scores(merged)

        return merged

    def _build_filters(self, query: SearchQueryDTO) -> dict[str, Any]:
        """Build filters from query.

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

    async def search_with_policy(
        self,
        query: str,
        policy_mode: SearchPolicyMode,
        **query_params: Any,
    ) -> SearchResponseDTO:
        """Search with a specific policy mode.

        Args:
            query: Search query string
            policy_mode: Policy mode to use
            **query_params: Additional query parameters

        Returns:
            SearchResponseDTO with results
        """
        policy = SearchPolicies.get_policy(policy_mode)

        search_query = SearchQueryDTO(
            query=query,
            top_k=policy.max_results,
            semantic_enabled=policy.semantic_enabled,
            include_explanation=policy.include_explanation,
            **query_params,
        )

        return await self.search(search_query, policy=policy)

    async def find_similar(
        self,
        item_id: int,
        content_type: SearchContentType,
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
        if not self._semantic_search:
            return []

        return await self._semantic_search.get_similar(
            item_id,
            content_type.value,
            top_k=top_k,
        )
