"""Search result explanation generation."""

from typing import Any

from app.bootstrap.logging import get_logger
from app.contracts.dto.search import (
    SearchContentType,
    SearchExplanationDTO,
    SearchQueryDTO,
    SearchResultItemDTO,
)

logger = get_logger(__name__)


class SearchExplainer:
    """Generates explanations for search results.

    Explains why a result matched a query.
    """

    def explain_result(
        self,
        result: SearchResultItemDTO,
        query: SearchQueryDTO,
    ) -> SearchExplanationDTO:
        """Generate explanation for a search result.

        Args:
            result: Search result
            query: Original query

        Returns:
            SearchExplanationDTO with explanation
        """
        keyword_matches = self._find_keyword_matches(result, query.query)
        score_components = self._compute_score_components(result)
        explanation_text = self._generate_explanation_text(
            result, query, keyword_matches
        )

        return SearchExplanationDTO(
            result_id=result.id,
            content_type=result.content_type,
            final_score=result.score,
            keyword_matches=keyword_matches,
            semantic_similarity=result.semantic_score,
            score_components=score_components,
            explanation_text=explanation_text,
        )

    def _find_keyword_matches(
        self,
        result: SearchResultItemDTO,
        query: str,
    ) -> list[dict[str, Any]]:
        """Find keyword matches in result.

        Args:
            result: Search result
            query: Query string

        Returns:
            List of keyword match info
        """
        matches = []
        query_lower = query.lower()
        query_terms = query_lower.split()

        # Check title
        if result.title:
            title_lower = result.title.lower()
            for term in query_terms:
                if term in title_lower:
                    matches.append({
                        "field": "title",
                        "term": term,
                        "context": result.title,
                    })

        # Check summary
        if result.summary:
            summary_lower = result.summary.lower()
            for term in query_terms:
                if term in summary_lower:
                    # Extract context around match
                    pos = summary_lower.find(term)
                    start = max(0, pos - 50)
                    end = min(len(result.summary), pos + len(term) + 50)
                    context = result.summary[start:end]
                    if start > 0:
                        context = "..." + context
                    if end < len(result.summary):
                        context = context + "..."

                    matches.append({
                        "field": "summary",
                        "term": term,
                        "context": context,
                    })

        # Check tags
        for tag in result.tags:
            tag_lower = tag.lower()
            for term in query_terms:
                if term in tag_lower:
                    matches.append({
                        "field": "tags",
                        "term": term,
                        "matched_tag": tag,
                    })

        return matches

    def _compute_score_components(
        self,
        result: SearchResultItemDTO,
    ) -> dict[str, float]:
        """Compute score component breakdown.

        Args:
            result: Search result

        Returns:
            Dict of score components
        """
        components: dict[str, float] = {}

        if result.keyword_score is not None:
            components["keyword_score"] = result.keyword_score

        if result.semantic_score is not None:
            components["semantic_score"] = result.semantic_score

        # Estimate component contributions
        if result.matched_by == "hybrid":
            components["hybrid_boost"] = 0.2

        # Add metadata-based components
        if result.metadata.get("heat_score"):
            components["heat_score"] = float(result.metadata["heat_score"]) / 100

        if result.metadata.get("trend_score"):
            components["trend_score"] = float(result.metadata["trend_score"])

        return components

    def _generate_explanation_text(
        self,
        result: SearchResultItemDTO,
        query: SearchQueryDTO,
        keyword_matches: list[dict[str, Any]],
    ) -> str:
        """Generate human-readable explanation.

        Args:
            result: Search result
            query: Original query
            keyword_matches: Keyword match info

        Returns:
            Explanation text
        """
        parts = []

        # Match type
        if result.matched_by == "hybrid":
            parts.append("Matched by both keyword and semantic search")
        elif result.matched_by == "keyword":
            parts.append("Matched by keyword search")
        elif result.matched_by == "semantic":
            parts.append("Matched by semantic similarity")

        # Keyword matches
        if keyword_matches:
            fields = set(m["field"] for m in keyword_matches)
            parts.append(f"Keywords found in: {', '.join(fields)}")

        # Semantic score
        if result.semantic_score is not None:
            similarity_pct = int(result.semantic_score * 100)
            parts.append(f"Semantic similarity: {similarity_pct}%")

        # Score
        parts.append(f"Final score: {result.score:.3f}")

        return ". ".join(parts) + "."

    def explain_batch(
        self,
        results: list[SearchResultItemDTO],
        query: SearchQueryDTO,
    ) -> list[SearchExplanationDTO]:
        """Generate explanations for multiple results.

        Args:
            results: Search results
            query: Original query

        Returns:
            List of explanations
        """
        return [self.explain_result(r, query) for r in results]

    def get_match_summary(
        self,
        result: SearchResultItemDTO,
        query: str,
    ) -> str:
        """Get a brief match summary.

        Args:
            result: Search result
            query: Query string

        Returns:
            Brief summary string
        """
        parts = []

        if result.matched_by:
            parts.append(result.matched_by)

        if result.matched_fields:
            parts.append(f"in {', '.join(result.matched_fields)}")

        if result.semantic_score is not None:
            parts.append(f"{int(result.semantic_score * 100)}% similar")

        return " | ".join(parts) if parts else "matched"


class SearchExplanationBuilder:
    """Builder for constructing search explanations."""

    def __init__(self) -> None:
        """Initialize builder."""
        self._result_id: int = 0
        self._content_type: SearchContentType = SearchContentType.TOPIC
        self._final_score: float = 0.0
        self._keyword_matches: list[dict[str, Any]] = []
        self._semantic_similarity: float | None = None
        self._score_components: dict[str, float] = {}
        self._explanation_parts: list[str] = []

    def for_result(
        self,
        result_id: int,
        content_type: SearchContentType,
    ) -> "SearchExplanationBuilder":
        """Set result identity.

        Args:
            result_id: Result ID
            content_type: Content type

        Returns:
            Self for chaining
        """
        self._result_id = result_id
        self._content_type = content_type
        return self

    def with_score(self, score: float) -> "SearchExplanationBuilder":
        """Set final score.

        Args:
            score: Final score

        Returns:
            Self for chaining
        """
        self._final_score = score
        return self

    def add_keyword_match(
        self,
        field: str,
        term: str,
        context: str | None = None,
    ) -> "SearchExplanationBuilder":
        """Add keyword match.

        Args:
            field: Field that matched
            term: Matched term
            context: Match context

        Returns:
            Self for chaining
        """
        match = {"field": field, "term": term}
        if context:
            match["context"] = context
        self._keyword_matches.append(match)
        return self

    def with_semantic_similarity(
        self,
        similarity: float,
    ) -> "SearchExplanationBuilder":
        """Set semantic similarity.

        Args:
            similarity: Similarity score

        Returns:
            Self for chaining
        """
        self._semantic_similarity = similarity
        return self

    def add_score_component(
        self,
        name: str,
        value: float,
    ) -> "SearchExplanationBuilder":
        """Add score component.

        Args:
            name: Component name
            value: Component value

        Returns:
            Self for chaining
        """
        self._score_components[name] = value
        return self

    def add_explanation(self, text: str) -> "SearchExplanationBuilder":
        """Add explanation text.

        Args:
            text: Explanation text

        Returns:
            Self for chaining
        """
        self._explanation_parts.append(text)
        return self

    def build(self) -> SearchExplanationDTO:
        """Build the explanation.

        Returns:
            SearchExplanationDTO
        """
        return SearchExplanationDTO(
            result_id=self._result_id,
            content_type=self._content_type,
            final_score=self._final_score,
            keyword_matches=self._keyword_matches,
            semantic_similarity=self._semantic_similarity,
            score_components=self._score_components,
            explanation_text=". ".join(self._explanation_parts) if self._explanation_parts else None,
        )
