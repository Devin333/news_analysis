"""Semantic result merger for combining search results."""

from typing import Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import SearchResultItemDTO

logger = get_logger(__name__)


class SemanticResultMerger:
    """Merger for combining keyword and semantic search results.

    Implements various merging strategies:
    - Score-based merging
    - Reciprocal Rank Fusion (RRF)
    - Weighted combination
    """

    def __init__(
        self,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
    ) -> None:
        """Initialize merger.

        Args:
            keyword_weight: Weight for keyword scores
            semantic_weight: Weight for semantic scores
        """
        self._keyword_weight = keyword_weight
        self._semantic_weight = semantic_weight

    def merge_weighted(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
    ) -> list[SearchResultItemDTO]:
        """Merge results using weighted score combination.

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results

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
                keyword_score * self._keyword_weight
                + semantic_score * self._semantic_weight
            )

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
                summary=base_result.summary or (semantic_result.summary if semantic_result else None),
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

    def merge_rrf(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
        *,
        k: int = 60,
    ) -> list[SearchResultItemDTO]:
        """Merge results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results
            k: RRF constant (default 60)

        Returns:
            Merged and ranked results
        """
        # Calculate RRF scores
        rrf_scores: dict[tuple[int, str], float] = {}
        result_map: dict[tuple[int, str], SearchResultItemDTO] = {}

        # Process keyword results
        for rank, result in enumerate(keyword_results, start=1):
            key = (result.id, result.content_type.value)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            result_map[key] = result
            result.keyword_score = result.score

        # Process semantic results
        for rank, result in enumerate(semantic_results, start=1):
            key = (result.id, result.content_type.value)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in result_map:
                result_map[key] = result
            else:
                # Update with semantic info
                result_map[key].semantic_score = result.score
                result_map[key].matched_by = "hybrid"

        # Build merged results
        merged: list[SearchResultItemDTO] = []
        for key, rrf_score in rrf_scores.items():
            result = result_map[key]
            result.score = rrf_score
            merged.append(result)

        # Sort by RRF score
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged

    def merge_interleaved(
        self,
        keyword_results: list[SearchResultItemDTO],
        semantic_results: list[SearchResultItemDTO],
    ) -> list[SearchResultItemDTO]:
        """Merge results by interleaving.

        Alternates between keyword and semantic results.

        Args:
            keyword_results: Keyword search results
            semantic_results: Semantic search results

        Returns:
            Interleaved results
        """
        seen: set[tuple[int, str]] = set()
        merged: list[SearchResultItemDTO] = []

        keyword_iter = iter(keyword_results)
        semantic_iter = iter(semantic_results)

        keyword_done = False
        semantic_done = False

        while not (keyword_done and semantic_done):
            # Add from keyword
            if not keyword_done:
                try:
                    result = next(keyword_iter)
                    key = (result.id, result.content_type.value)
                    if key not in seen:
                        seen.add(key)
                        result.keyword_score = result.score
                        merged.append(result)
                except StopIteration:
                    keyword_done = True

            # Add from semantic
            if not semantic_done:
                try:
                    result = next(semantic_iter)
                    key = (result.id, result.content_type.value)
                    if key not in seen:
                        seen.add(key)
                        result.semantic_score = result.score
                        merged.append(result)
                    else:
                        # Update existing with semantic score
                        for m in merged:
                            if m.id == result.id and m.content_type == result.content_type:
                                m.semantic_score = result.score
                                m.matched_by = "hybrid"
                                break
                except StopIteration:
                    semantic_done = True

        # Assign scores based on position
        for i, result in enumerate(merged):
            result.score = 1.0 - (i / len(merged)) if merged else 0.0

        return merged

    def boost_hybrid_matches(
        self,
        results: list[SearchResultItemDTO],
        boost_factor: float = 1.2,
    ) -> list[SearchResultItemDTO]:
        """Boost scores for results that matched both keyword and semantic.

        Args:
            results: Merged results
            boost_factor: Multiplier for hybrid matches

        Returns:
            Results with boosted hybrid scores
        """
        for result in results:
            if result.matched_by == "hybrid":
                result.score *= boost_factor

        # Re-sort
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def normalize_scores(
        self,
        results: list[SearchResultItemDTO],
    ) -> list[SearchResultItemDTO]:
        """Normalize scores to 0-1 range.

        Args:
            results: Results to normalize

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        max_score = max(r.score for r in results)
        min_score = min(r.score for r in results)

        if max_score == min_score:
            for r in results:
                r.score = 1.0
        else:
            for r in results:
                r.score = (r.score - min_score) / (max_score - min_score)

        return results
