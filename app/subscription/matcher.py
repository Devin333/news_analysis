"""Subscription matcher for matching content against subscriptions."""

from typing import Any

from app.bootstrap.logging import get_logger
from app.subscription.policies import MatchPolicyConfig, SubscriptionMatchPolicies

logger = get_logger(__name__)


class SubscriptionMatcher:
    """Matcher for matching content against subscriptions.

    Supports:
    - Keyword matching
    - Tag matching
    - Entity matching
    - Board matching
    - Semantic matching (optional)
    """

    def __init__(
        self,
        semantic_search: Any | None = None,
    ) -> None:
        """Initialize matcher.

        Args:
            semantic_search: Optional semantic search for semantic matching.
        """
        self._semantic_search = semantic_search

    def match_topic(
        self,
        subscription: Any,
        topic_title: str,
        topic_summary: str | None = None,
        topic_tags: list[str] | None = None,
        board_type: str | None = None,
    ) -> dict[str, Any]:
        """Match a topic against a subscription.

        Args:
            subscription: Subscription model.
            topic_title: Topic title.
            topic_summary: Topic summary.
            topic_tags: Topic tags.
            board_type: Topic board type.

        Returns:
            Match result dict with matched, score, reason, matched_fields.
        """
        policy = SubscriptionMatchPolicies.for_subscription_type(
            subscription.subscription_type
        )

        # Check board filter first
        if subscription.board_type and board_type:
            if subscription.board_type != board_type:
                return self._no_match("Board type mismatch")

        # Match based on subscription type
        if subscription.subscription_type == "query":
            return self._match_query(
                subscription.query,
                topic_title,
                topic_summary,
                policy,
            )
        elif subscription.subscription_type == "tag":
            return self._match_tags(
                subscription.tags_json or [],
                topic_tags or [],
                policy,
            )
        elif subscription.subscription_type == "entity":
            # Entity matching would need entity extraction
            return self._no_match("Entity matching not implemented")
        elif subscription.subscription_type == "topic":
            # Topic subscription matches specific topic ID
            return self._no_match("Topic ID matching handled separately")
        elif subscription.subscription_type == "board":
            # Board already checked above
            return self._match_board(subscription.board_type, board_type)
        else:
            return self._no_match(f"Unknown subscription type: {subscription.subscription_type}")

    def _match_query(
        self,
        query: str | None,
        title: str,
        summary: str | None,
        policy: MatchPolicyConfig,
    ) -> dict[str, Any]:
        """Match query against title and summary.

        Args:
            query: Search query.
            title: Content title.
            summary: Content summary.
            policy: Match policy.

        Returns:
            Match result.
        """
        if not query:
            return self._no_match("No query specified")

        query_lower = query.lower() if not policy.case_sensitive else query
        title_lower = title.lower() if not policy.case_sensitive else title
        summary_lower = (summary.lower() if summary else "") if not policy.case_sensitive else (summary or "")

        matched_fields = []
        score = 0.0

        # Check title
        if policy.partial_match:
            if query_lower in title_lower:
                matched_fields.append("title")
                score += 0.6
        else:
            if query_lower == title_lower:
                matched_fields.append("title")
                score += 0.8

        # Check summary
        if summary_lower:
            if policy.partial_match:
                if query_lower in summary_lower:
                    matched_fields.append("summary")
                    score += 0.4
            else:
                if query_lower == summary_lower:
                    matched_fields.append("summary")
                    score += 0.4

        # Check individual terms
        query_terms = query_lower.split()
        if len(query_terms) > 1:
            term_matches = sum(
                1 for term in query_terms
                if term in title_lower or term in summary_lower
            )
            term_score = term_matches / len(query_terms) * 0.5
            score = max(score, term_score)
            if term_matches > 0 and not matched_fields:
                matched_fields.append("terms")

        if score >= policy.min_score and matched_fields:
            return {
                "matched": True,
                "score": min(1.0, score),
                "reason": f"Query '{query}' matched in {', '.join(matched_fields)}",
                "matched_fields": matched_fields,
            }

        return self._no_match(f"Query '{query}' did not match")

    def _match_tags(
        self,
        subscription_tags: list[str],
        content_tags: list[str],
        policy: MatchPolicyConfig,
    ) -> dict[str, Any]:
        """Match tags.

        Args:
            subscription_tags: Tags to match.
            content_tags: Content tags.
            policy: Match policy.

        Returns:
            Match result.
        """
        if not subscription_tags:
            return self._no_match("No tags specified")

        if not content_tags:
            return self._no_match("Content has no tags")

        # Normalize tags
        sub_tags = {t.lower() for t in subscription_tags}
        cont_tags = {t.lower() for t in content_tags}

        matched_tags = sub_tags & cont_tags

        if policy.require_all_tags:
            if matched_tags == sub_tags:
                return {
                    "matched": True,
                    "score": 1.0,
                    "reason": f"All tags matched: {matched_tags}",
                    "matched_fields": ["tags"],
                    "matched_tags": list(matched_tags),
                }
            return self._no_match("Not all tags matched")
        else:
            if matched_tags:
                score = len(matched_tags) / len(sub_tags)
                if score >= policy.min_score:
                    return {
                        "matched": True,
                        "score": score,
                        "reason": f"Tags matched: {matched_tags}",
                        "matched_fields": ["tags"],
                        "matched_tags": list(matched_tags),
                    }

        return self._no_match("No tags matched")

    def _match_board(
        self,
        subscription_board: str | None,
        content_board: str | None,
    ) -> dict[str, Any]:
        """Match board type.

        Args:
            subscription_board: Subscription board filter.
            content_board: Content board type.

        Returns:
            Match result.
        """
        if not subscription_board:
            return self._no_match("No board specified")

        if subscription_board == content_board:
            return {
                "matched": True,
                "score": 1.0,
                "reason": f"Board matched: {subscription_board}",
                "matched_fields": ["board_type"],
            }

        return self._no_match(f"Board mismatch: {subscription_board} != {content_board}")

    def _no_match(self, reason: str) -> dict[str, Any]:
        """Create no-match result.

        Args:
            reason: Reason for no match.

        Returns:
            No-match result dict.
        """
        return {
            "matched": False,
            "score": 0.0,
            "reason": reason,
            "matched_fields": [],
        }

    async def match_semantic(
        self,
        subscription_query: str,
        content_text: str,
        min_score: float = 0.7,
    ) -> dict[str, Any]:
        """Match using semantic similarity.

        Args:
            subscription_query: Query to match.
            content_text: Content text.
            min_score: Minimum similarity score.

        Returns:
            Match result.
        """
        if not self._semantic_search:
            return self._no_match("Semantic search not configured")

        # This would use embedding similarity
        # Placeholder implementation
        return self._no_match("Semantic matching not implemented")
