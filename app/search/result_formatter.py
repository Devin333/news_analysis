"""Result formatter for search results."""

from datetime import datetime
from typing import Any

from app.contracts.dto.search import (
    SearchContentType,
    SearchResultItemDTO,
    SearchResponseDTO,
)


class SearchResultFormatter:
    """Formatter for search results.

    Converts raw database results to unified format.
    """

    def format_topic_result(
        self,
        row: Any,
        *,
        score: float = 0.0,
        matched_by: str | None = None,
        matched_fields: list[str] | None = None,
        highlights: dict[str, list[str]] | None = None,
    ) -> SearchResultItemDTO:
        """Format a topic result.

        Args:
            row: Database row
            score: Relevance score
            matched_by: How it was matched
            matched_fields: Fields that matched
            highlights: Highlighted snippets

        Returns:
            Formatted SearchResultItemDTO
        """
        return SearchResultItemDTO(
            id=row.id,
            content_type=SearchContentType.TOPIC,
            score=score,
            title=row.title,
            summary=getattr(row, "summary", None),
            board_type=getattr(row, "board_type", None),
            tags=getattr(row, "tags", []) or [],
            created_at=getattr(row, "first_seen_at", None),
            updated_at=getattr(row, "last_seen_at", None),
            matched_by=matched_by,
            matched_fields=matched_fields or [],
            highlights=highlights or {},
            metadata={
                "heat_score": float(getattr(row, "heat_score", 0) or 0),
                "trend_score": float(getattr(row, "trend_score", 0) or 0),
                "item_count": getattr(row, "item_count", 0),
                "source_count": getattr(row, "source_count", 0),
            },
        )

    def format_item_result(
        self,
        row: Any,
        *,
        score: float = 0.0,
        matched_by: str | None = None,
        matched_fields: list[str] | None = None,
        highlights: dict[str, list[str]] | None = None,
    ) -> SearchResultItemDTO:
        """Format an item result.

        Args:
            row: Database row
            score: Relevance score
            matched_by: How it was matched
            matched_fields: Fields that matched
            highlights: Highlighted snippets

        Returns:
            Formatted SearchResultItemDTO
        """
        return SearchResultItemDTO(
            id=row.id,
            content_type=SearchContentType.ITEM,
            score=score,
            title=row.title,
            excerpt=getattr(row, "excerpt", None),
            board_type=getattr(row, "board_type_candidate", None),
            tags=getattr(row, "tags", []) or [],
            created_at=getattr(row, "published_at", None) or getattr(row, "created_at", None),
            matched_by=matched_by,
            matched_fields=matched_fields or [],
            highlights=highlights or {},
            metadata={
                "content_type": getattr(row, "content_type", None),
                "author": getattr(row, "author", None),
                "source_id": getattr(row, "source_id", None),
            },
        )

    def format_entity_result(
        self,
        row: Any,
        *,
        score: float = 0.0,
        matched_by: str | None = None,
        matched_fields: list[str] | None = None,
    ) -> SearchResultItemDTO:
        """Format an entity result.

        Args:
            row: Database row
            score: Relevance score
            matched_by: How it was matched
            matched_fields: Fields that matched

        Returns:
            Formatted SearchResultItemDTO
        """
        return SearchResultItemDTO(
            id=row.id,
            content_type=SearchContentType.ENTITY,
            score=score,
            title=getattr(row, "name", "") or getattr(row, "canonical_name", ""),
            summary=getattr(row, "description", None),
            matched_by=matched_by,
            matched_fields=matched_fields or [],
            metadata={
                "entity_type": getattr(row, "entity_type", None),
                "aliases": getattr(row, "aliases", []),
                "mention_count": getattr(row, "mention_count", 0),
            },
        )

    def format_history_result(
        self,
        row: Any,
        *,
        score: float = 0.0,
        matched_by: str | None = None,
    ) -> SearchResultItemDTO:
        """Format a history/memory result.

        Args:
            row: Database row
            score: Relevance score
            matched_by: How it was matched

        Returns:
            Formatted SearchResultItemDTO
        """
        return SearchResultItemDTO(
            id=row.id,
            content_type=SearchContentType.HISTORY,
            score=score,
            title=getattr(row, "title", "") or f"History #{row.id}",
            summary=getattr(row, "history_summary", None),
            created_at=getattr(row, "created_at", None),
            matched_by=matched_by,
            metadata={
                "topic_id": getattr(row, "topic_id", None),
                "event_count": getattr(row, "event_count", 0),
            },
        )

    def add_highlights(
        self,
        result: SearchResultItemDTO,
        query: str,
        *,
        max_snippets: int = 3,
        snippet_length: int = 150,
    ) -> SearchResultItemDTO:
        """Add highlighted snippets to result.

        Args:
            result: Search result
            query: Original query
            max_snippets: Maximum snippets per field
            snippet_length: Length of each snippet

        Returns:
            Result with highlights
        """
        query_lower = query.lower()
        highlights: dict[str, list[str]] = {}

        # Highlight title
        if result.title and query_lower in result.title.lower():
            highlights["title"] = [self._highlight_text(result.title, query)]

        # Highlight summary
        if result.summary and query_lower in result.summary.lower():
            snippets = self._extract_snippets(
                result.summary, query, max_snippets, snippet_length
            )
            if snippets:
                highlights["summary"] = snippets

        # Highlight excerpt
        if result.excerpt and query_lower in result.excerpt.lower():
            snippets = self._extract_snippets(
                result.excerpt, query, max_snippets, snippet_length
            )
            if snippets:
                highlights["excerpt"] = snippets

        result.highlights = highlights
        return result

    def _highlight_text(self, text: str, query: str) -> str:
        """Add highlight markers to text.

        Args:
            text: Text to highlight
            query: Query to highlight

        Returns:
            Text with highlight markers
        """
        import re

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        return pattern.sub(f"<mark>{query}</mark>", text)

    def _extract_snippets(
        self,
        text: str,
        query: str,
        max_snippets: int,
        snippet_length: int,
    ) -> list[str]:
        """Extract snippets containing query.

        Args:
            text: Full text
            query: Query to find
            max_snippets: Maximum snippets
            snippet_length: Length of each snippet

        Returns:
            List of snippets
        """
        snippets = []
        query_lower = query.lower()
        text_lower = text.lower()

        start = 0
        while len(snippets) < max_snippets:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break

            # Extract snippet around match
            snippet_start = max(0, pos - snippet_length // 2)
            snippet_end = min(len(text), pos + len(query) + snippet_length // 2)

            snippet = text[snippet_start:snippet_end]

            # Add ellipsis if truncated
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(text):
                snippet = snippet + "..."

            # Highlight the match
            snippet = self._highlight_text(snippet, query)
            snippets.append(snippet)

            start = pos + len(query)

        return snippets

    def merge_duplicate_results(
        self,
        results: list[SearchResultItemDTO],
    ) -> list[SearchResultItemDTO]:
        """Merge duplicate results.

        Args:
            results: List of results

        Returns:
            Deduplicated results
        """
        seen: dict[tuple[int, str], SearchResultItemDTO] = {}

        for result in results:
            key = (result.id, result.content_type.value)

            if key in seen:
                existing = seen[key]
                # Keep higher score
                if result.score > existing.score:
                    seen[key] = result
                # Merge matched fields
                existing.matched_fields = list(
                    set(existing.matched_fields + result.matched_fields)
                )
                # Update matched_by if hybrid
                if existing.matched_by != result.matched_by:
                    existing.matched_by = "hybrid"
            else:
                seen[key] = result

        return list(seen.values())
