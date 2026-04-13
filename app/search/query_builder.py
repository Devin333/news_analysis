"""Query builder for PostgreSQL search queries."""

from datetime import datetime
from typing import Any

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class SearchQueryBuilder:
    """Builder for constructing search queries.

    Supports building PostgreSQL full-text search queries.
    """

    def __init__(self) -> None:
        """Initialize query builder."""
        self._conditions: list[str] = []
        self._params: dict[str, Any] = {}
        self._order_by: list[str] = []
        self._limit: int | None = None
        self._offset: int | None = None

    def with_text_search(
        self,
        query: str,
        fields: list[str],
        *,
        param_name: str = "query",
    ) -> "SearchQueryBuilder":
        """Add full-text search condition.

        Args:
            query: Search query string
            fields: Fields to search in
            param_name: Parameter name for binding

        Returns:
            Self for chaining
        """
        if not query.strip():
            return self

        # Build tsvector expression
        tsvector_parts = [f"coalesce({f}, '')" for f in fields]
        tsvector_expr = " || ' ' || ".join(tsvector_parts)

        # Use plainto_tsquery for simple queries
        condition = f"to_tsvector('english', {tsvector_expr}) @@ plainto_tsquery('english', :{param_name})"
        self._conditions.append(condition)
        self._params[param_name] = query

        return self

    def with_like_search(
        self,
        query: str,
        fields: list[str],
        *,
        param_name: str = "like_query",
    ) -> "SearchQueryBuilder":
        """Add LIKE search condition.

        Args:
            query: Search query string
            fields: Fields to search in
            param_name: Parameter name

        Returns:
            Self for chaining
        """
        if not query.strip():
            return self

        like_conditions = [f"LOWER({f}) LIKE :{param_name}" for f in fields]
        condition = f"({' OR '.join(like_conditions)})"
        self._conditions.append(condition)
        self._params[param_name] = f"%{query.lower()}%"

        return self

    def with_board_filter(
        self,
        board_types: list[str],
        *,
        field: str = "board_type",
    ) -> "SearchQueryBuilder":
        """Add board type filter.

        Args:
            board_types: List of board types
            field: Field name

        Returns:
            Self for chaining
        """
        if not board_types:
            return self

        placeholders = [f":board_{i}" for i in range(len(board_types))]
        condition = f"{field} IN ({', '.join(placeholders)})"
        self._conditions.append(condition)

        for i, bt in enumerate(board_types):
            self._params[f"board_{i}"] = bt

        return self

    def with_tags_filter(
        self,
        tags: list[str],
        *,
        field: str = "tags",
        match_all: bool = False,
    ) -> "SearchQueryBuilder":
        """Add tags filter.

        Args:
            tags: List of tags to match
            field: Field name (assumes JSONB array)
            match_all: Whether all tags must match

        Returns:
            Self for chaining
        """
        if not tags:
            return self

        if match_all:
            # All tags must be present
            for i, tag in enumerate(tags):
                condition = f"{field} @> :tag_{i}::jsonb"
                self._conditions.append(condition)
                self._params[f"tag_{i}"] = f'["{tag}"]'
        else:
            # Any tag matches
            placeholders = [f":tag_{i}" for i in range(len(tags))]
            condition = f"{field} ?| ARRAY[{', '.join(placeholders)}]"
            self._conditions.append(condition)
            for i, tag in enumerate(tags):
                self._params[f"tag_{i}"] = tag

        return self

    def with_date_range(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        *,
        field: str = "created_at",
    ) -> "SearchQueryBuilder":
        """Add date range filter.

        Args:
            date_from: Start date
            date_to: End date
            field: Date field name

        Returns:
            Self for chaining
        """
        if date_from:
            self._conditions.append(f"{field} >= :date_from")
            self._params["date_from"] = date_from

        if date_to:
            self._conditions.append(f"{field} <= :date_to")
            self._params["date_to"] = date_to

        return self

    def with_status_filter(
        self,
        status: str,
        *,
        field: str = "status",
    ) -> "SearchQueryBuilder":
        """Add status filter.

        Args:
            status: Status value
            field: Field name

        Returns:
            Self for chaining
        """
        self._conditions.append(f"{field} = :status")
        self._params["status"] = status
        return self

    def with_content_type_filter(
        self,
        content_types: list[str],
        *,
        field: str = "content_type",
    ) -> "SearchQueryBuilder":
        """Add content type filter.

        Args:
            content_types: List of content types
            field: Field name

        Returns:
            Self for chaining
        """
        if not content_types:
            return self

        placeholders = [f":ct_{i}" for i in range(len(content_types))]
        condition = f"{field} IN ({', '.join(placeholders)})"
        self._conditions.append(condition)

        for i, ct in enumerate(content_types):
            self._params[f"ct_{i}"] = ct

        return self

    def order_by(
        self,
        field: str,
        *,
        desc: bool = True,
    ) -> "SearchQueryBuilder":
        """Add order by clause.

        Args:
            field: Field to order by
            desc: Whether to order descending

        Returns:
            Self for chaining
        """
        direction = "DESC" if desc else "ASC"
        self._order_by.append(f"{field} {direction}")
        return self

    def order_by_relevance(
        self,
        query: str,
        fields: list[str],
    ) -> "SearchQueryBuilder":
        """Order by text search relevance.

        Args:
            query: Search query
            fields: Fields to compute relevance from

        Returns:
            Self for chaining
        """
        tsvector_parts = [f"coalesce({f}, '')" for f in fields]
        tsvector_expr = " || ' ' || ".join(tsvector_parts)

        rank_expr = f"ts_rank(to_tsvector('english', {tsvector_expr}), plainto_tsquery('english', :rank_query))"
        self._order_by.insert(0, f"{rank_expr} DESC")
        self._params["rank_query"] = query

        return self

    def limit(self, limit: int) -> "SearchQueryBuilder":
        """Set result limit.

        Args:
            limit: Maximum results

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> "SearchQueryBuilder":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self._offset = offset
        return self

    def build_where_clause(self) -> tuple[str, dict[str, Any]]:
        """Build WHERE clause.

        Returns:
            Tuple of (clause string, parameters dict)
        """
        if not self._conditions:
            return "", {}

        clause = " AND ".join(self._conditions)
        return f"WHERE {clause}", self._params

    def build_order_clause(self) -> str:
        """Build ORDER BY clause.

        Returns:
            ORDER BY clause string
        """
        if not self._order_by:
            return ""

        return f"ORDER BY {', '.join(self._order_by)}"

    def build_limit_clause(self) -> str:
        """Build LIMIT/OFFSET clause.

        Returns:
            LIMIT/OFFSET clause string
        """
        parts = []
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")
        if self._offset is not None:
            parts.append(f"OFFSET {self._offset}")
        return " ".join(parts)

    def build(self, base_query: str) -> tuple[str, dict[str, Any]]:
        """Build complete query.

        Args:
            base_query: Base SELECT query

        Returns:
            Tuple of (complete query, parameters)
        """
        where_clause, params = self.build_where_clause()
        order_clause = self.build_order_clause()
        limit_clause = self.build_limit_clause()

        query = f"{base_query} {where_clause} {order_clause} {limit_clause}".strip()
        return query, params

    def reset(self) -> "SearchQueryBuilder":
        """Reset builder state.

        Returns:
            Self for chaining
        """
        self._conditions.clear()
        self._params.clear()
        self._order_by.clear()
        self._limit = None
        self._offset = None
        return self
