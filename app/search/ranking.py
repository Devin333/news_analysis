"""Search result ranking."""

from typing import Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import SearchQueryDTO, SearchResultItemDTO
from app.contracts.protocols.search import SearchRankerProtocol

logger = get_logger(__name__)


class SearchRanker(SearchRankerProtocol):
    """Ranker for search results.

    Applies additional ranking factors to search results.
    """

    def __init__(
        self,
        recency_weight: float = 0.1,
        board_match_weight: float = 0.1,
        review_weight: float = 0.1,
    ) -> None:
        """Initialize ranker.

        Args:
            recency_weight: Weight for recency boost
            board_match_weight: Weight for board match boost
            review_weight: Weight for review status boost
        """
        self._recency_weight = recency_weight
        self._board_match_weight = board_match_weight
        self._review_weight = review_weight

    def rank_results(
        self,
        results: list[SearchResultItemDTO],
        query: SearchQueryDTO,
    ) -> list[SearchResultItemDTO]:
        """Rank search results.

        Applies additional ranking factors:
        - Recency boost
        - Board match boost
        - Review status boost

        Args:
            results: Unranked results
            query: Original query

        Returns:
            Ranked results
        """
        if not results:
            return results

        for result in results:
            boost = self._calculate_boost(result, query)
            result.score = result.score * (1 + boost)

        # Sort by adjusted score
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _calculate_boost(
        self,
        result: SearchResultItemDTO,
        query: SearchQueryDTO,
    ) -> float:
        """Calculate boost for a result.

        Args:
            result: Search result
            query: Original query

        Returns:
            Boost factor
        """
        boost = 0.0

        # Recency boost
        if result.updated_at:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if result.updated_at.tzinfo is None:
                result.updated_at = result.updated_at.replace(tzinfo=timezone.utc)
            age_hours = (now - result.updated_at).total_seconds() / 3600
            if age_hours < 24:
                boost += self._recency_weight * (1 - age_hours / 24)
            elif age_hours < 72:
                boost += self._recency_weight * 0.5 * (1 - (age_hours - 24) / 48)

        # Board match boost
        if query.board_filter and result.board_type:
            if result.board_type in query.board_filter:
                boost += self._board_match_weight

        # Review status boost (from metadata)
        if result.metadata.get("review_passed"):
            boost += self._review_weight

        return boost

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
        # Build lookup maps
        keyword_map: dict[tuple[int, str], SearchResultItemDTO] = {
            (r.id, r.content_type.value): r for r in keyword_results
        }
        semantic_map: dict[tuple[int, str], SearchResultItemDTO] = {
            (r.id, r.content_type.value): r for r in semantic_results
        }

        # Get all unique keys
        all_keys = set(keyword_map.keys()) | set(semantic_map.keys())

        merged: list[SearchResultItemDTO] = []

        for key in all_keys:
            keyword_result = keyword_map.get(key)
            semantic_result = semantic_map.get(key)

            # Calculate combined score
            keyword_score = keyword_result.score if keyword_result else 0.0
            semantic_score = semantic_result.score if semantic_result else 0.0

            combined_score = (
                keyword_score * keyword_weight
                + semantic_score * semantic_weight
            )

            # Boost for hybrid match
            if keyword_result and semantic_result:
                combined_score *= 1.2

            # Use the result with more information
            base_result = keyword_result or semantic_result
            if base_result is None:
                continue

            # Create merged result
            merged_result = SearchResultItemDTO(
                id=base_result.id,
                content_type=base_result.content_type,
                score=combined_score,
                title=base_result.title,
                summary=base_result.summary,
                excerpt=base_result.excerpt,
                board_type=base_result.board_type,
                tags=base_result.tags,
                created_at=base_result.created_at,
                updated_at=base_result.updated_at,
                matched_by="hybrid" if keyword_result and semantic_result else base_result.matched_by,
                matched_fields=base_result.matched_fields,
                keyword_score=keyword_score if keyword_score > 0 else None,
                semantic_score=semantic_score if semantic_score > 0 else None,
                highlights=base_result.highlights,
                metadata=base_result.metadata,
            )

            merged.append(merged_result)

        # Sort by combined score
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged

    def diversify_results(
        self,
        results: list[SearchResultItemDTO],
        *,
        max_per_board: int = 5,
    ) -> list[SearchResultItemDTO]:
        """Diversify results by board type.

        Args:
            results: Ranked results
            max_per_board: Maximum results per board

        Returns:
            Diversified results
        """
        board_counts: dict[str, int] = {}
        diversified: list[SearchResultItemDTO] = []

        for result in results:
            board = result.board_type or "general"
            count = board_counts.get(board, 0)

            if count < max_per_board:
                diversified.append(result)
                board_counts[board] = count + 1

        return diversified
