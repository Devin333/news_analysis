"""Keyword search implementation."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import SearchContentType, SearchResultItemDTO
from app.contracts.protocols.search import KeywordSearchProtocol
from app.search.query_builder import SearchQueryBuilder

logger = get_logger(__name__)


class KeywordSearch(KeywordSearchProtocol):
    """Keyword-based search implementation.

    Supports:
    - Title search
    - Summary search
    - Tags filtering
    - Board/content_type/date filtering
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize keyword search.

        Args:
            session: Database session
        """
        self._session = session

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
        filters = filters or {}
        results: list[SearchResultItemDTO] = []

        # Search topics
        topic_results = await self._search_topics(query, filters, limit)
        results.extend(topic_results)

        # Search items if needed
        if not filters.get("topics_only"):
            item_results = await self._search_items(query, filters, limit)
            results.extend(item_results)

        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def _search_topics(
        self,
        query: str,
        filters: dict,
        limit: int,
    ) -> list[SearchResultItemDTO]:
        """Search topics.

        Args:
            query: Search query
            filters: Filters
            limit: Maximum results

        Returns:
            List of topic results
        """
        builder = SearchQueryBuilder()

        # Add text search
        builder.with_text_search(query, ["title", "summary"])

        # Add filters
        if filters.get("board_type"):
            builder.with_board_filter(filters["board_type"])

        if filters.get("tags"):
            builder.with_tags_filter(filters["tags"])

        if filters.get("date_from") or filters.get("date_to"):
            builder.with_date_range(
                filters.get("date_from"),
                filters.get("date_to"),
                field="last_seen_at",
            )

        # Active topics only
        builder.with_status_filter("active")

        # Order by relevance
        builder.order_by_relevance(query, ["title", "summary"])
        builder.order_by("last_seen_at", desc=True)
        builder.limit(limit)

        # Build query
        base_query = """
            SELECT 
                id, title, summary, board_type, 
                heat_score, trend_score, item_count,
                first_seen_at, last_seen_at,
                ts_rank(
                    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, '')),
                    plainto_tsquery('english', :rank_query)
                ) as relevance_score
            FROM topics
        """

        sql, params = builder.build(base_query)

        try:
            result = await self._session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                SearchResultItemDTO(
                    id=row.id,
                    content_type=SearchContentType.TOPIC,
                    score=float(row.relevance_score) if row.relevance_score else 0.0,
                    title=row.title,
                    summary=row.summary,
                    board_type=row.board_type,
                    created_at=row.first_seen_at,
                    updated_at=row.last_seen_at,
                    matched_fields=["title", "summary"],
                    metadata={
                        "heat_score": float(row.heat_score) if row.heat_score else 0.0,
                        "trend_score": float(row.trend_score) if row.trend_score else 0.0,
                        "item_count": row.item_count,
                    },
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Topic search failed: {e}")
            return []

    async def _search_items(
        self,
        query: str,
        filters: dict,
        limit: int,
    ) -> list[SearchResultItemDTO]:
        """Search normalized items.

        Args:
            query: Search query
            filters: Filters
            limit: Maximum results

        Returns:
            List of item results
        """
        builder = SearchQueryBuilder()

        # Add text search
        builder.with_text_search(query, ["title", "clean_text", "excerpt"])

        # Add filters
        if filters.get("board_type"):
            builder.with_board_filter(
                filters["board_type"],
                field="board_type_candidate",
            )

        if filters.get("content_type"):
            builder.with_content_type_filter(filters["content_type"])

        if filters.get("date_from") or filters.get("date_to"):
            builder.with_date_range(
                filters.get("date_from"),
                filters.get("date_to"),
                field="published_at",
            )

        # Order by relevance
        builder.order_by_relevance(query, ["title", "clean_text"])
        builder.order_by("published_at", desc=True)
        builder.limit(limit)

        base_query = """
            SELECT 
                id, title, excerpt, clean_text,
                content_type, board_type_candidate,
                published_at, created_at,
                ts_rank(
                    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(clean_text, '')),
                    plainto_tsquery('english', :rank_query)
                ) as relevance_score
            FROM normalized_items
        """

        sql, params = builder.build(base_query)

        try:
            result = await self._session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                SearchResultItemDTO(
                    id=row.id,
                    content_type=SearchContentType.ITEM,
                    score=float(row.relevance_score) if row.relevance_score else 0.0,
                    title=row.title,
                    excerpt=row.excerpt,
                    board_type=row.board_type_candidate,
                    created_at=row.published_at or row.created_at,
                    matched_fields=["title", "clean_text"],
                    metadata={
                        "content_type": row.content_type,
                    },
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Item search failed: {e}")
            return []

    async def search_by_title(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[SearchResultItemDTO]:
        """Search by title only.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of results
        """
        builder = SearchQueryBuilder()
        builder.with_like_search(query, ["title"])
        builder.with_status_filter("active")
        builder.order_by("last_seen_at", desc=True)
        builder.limit(limit)

        base_query = "SELECT id, title, summary, board_type, last_seen_at FROM topics"
        sql, params = builder.build(base_query)

        try:
            result = await self._session.execute(text(sql), params)
            rows = result.fetchall()

            return [
                SearchResultItemDTO(
                    id=row.id,
                    content_type=SearchContentType.TOPIC,
                    score=1.0,  # Exact match
                    title=row.title,
                    summary=row.summary,
                    board_type=row.board_type,
                    updated_at=row.last_seen_at,
                    matched_fields=["title"],
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Title search failed: {e}")
            return []

    async def search_by_tags(
        self,
        tags: list[str],
        *,
        match_all: bool = False,
        limit: int = 20,
    ) -> list[SearchResultItemDTO]:
        """Search by tags.

        Args:
            tags: Tags to search for
            match_all: Whether all tags must match
            limit: Maximum results

        Returns:
            List of results
        """
        # This would need a join with topic_tags table
        # Simplified implementation
        return []
