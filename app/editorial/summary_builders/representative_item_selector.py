"""Representative item selector for topics.

This module provides functionality to select the most representative
item from a topic's item collection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from app.bootstrap.logging import get_logger
from app.contracts.dto.normalized_item import NormalizedItemDTO

logger = get_logger(__name__)


@dataclass
class SelectionCriteria:
    """Criteria weights for representative item selection."""

    # Weight for recency (newer is better)
    recency_weight: float = 0.3

    # Weight for content quality
    quality_weight: float = 0.25

    # Weight for content length (moderate length preferred)
    length_weight: float = 0.2

    # Weight for title informativeness
    title_weight: float = 0.15

    # Weight for source trust (if available)
    source_trust_weight: float = 0.1


@dataclass
class ScoredItem:
    """Item with selection score."""

    item: NormalizedItemDTO
    score: float
    score_breakdown: dict[str, float]


class RepresentativeItemSelector:
    """Selects the most representative item from a topic.

    The representative item is chosen based on:
    - Recency (newer items preferred)
    - Content quality score
    - Content length (moderate length preferred)
    - Title informativeness
    - Source trust score
    """

    def __init__(
        self,
        criteria: SelectionCriteria | None = None,
    ) -> None:
        """Initialize the selector.

        Args:
            criteria: Selection criteria weights.
        """
        self._criteria = criteria or SelectionCriteria()

    def select(
        self,
        items: Sequence[NormalizedItemDTO],
        *,
        source_trust_scores: dict[int, float] | None = None,
    ) -> NormalizedItemDTO | None:
        """Select the most representative item.

        Args:
            items: List of items to select from.
            source_trust_scores: Optional mapping of source_id to trust score.

        Returns:
            The most representative item, or None if no items.
        """
        if not items:
            return None

        if len(items) == 1:
            return items[0]

        scored_items = self.score_items(items, source_trust_scores=source_trust_scores)
        return scored_items[0].item

    def score_items(
        self,
        items: Sequence[NormalizedItemDTO],
        *,
        source_trust_scores: dict[int, float] | None = None,
    ) -> list[ScoredItem]:
        """Score all items and return sorted by score.

        Args:
            items: List of items to score.
            source_trust_scores: Optional mapping of source_id to trust score.

        Returns:
            List of ScoredItems sorted by score descending.
        """
        trust_scores = source_trust_scores or {}
        scored: list[ScoredItem] = []

        # Find min/max for normalization
        now = datetime.now(timezone.utc)
        timestamps = [
            i.published_at for i in items if i.published_at is not None
        ]
        min_time = min(timestamps) if timestamps else now
        max_time = max(timestamps) if timestamps else now
        time_range = (max_time - min_time).total_seconds() or 1.0

        lengths = [len(i.clean_text or "") for i in items]
        max_length = max(lengths) if lengths else 1
        ideal_length = max_length * 0.6  # Prefer moderate length

        for item in items:
            breakdown: dict[str, float] = {}

            # Recency score
            if item.published_at:
                age_seconds = (now - item.published_at).total_seconds()
                # Normalize: newer = higher score
                recency = 1.0 - min(age_seconds / (7 * 24 * 3600), 1.0)  # 7 days max
            else:
                recency = 0.5
            breakdown["recency"] = recency

            # Quality score (use item's quality_score if available)
            quality = item.quality_score if item.quality_score else 0.5
            breakdown["quality"] = quality

            # Length score (prefer moderate length)
            content_length = len(item.clean_text or "")
            if max_length > 0:
                # Score peaks at ideal_length, decreases for too short or too long
                length_diff = abs(content_length - ideal_length) / max_length
                length_score = 1.0 - min(length_diff, 1.0)
            else:
                length_score = 0.5
            breakdown["length"] = length_score

            # Title informativeness (based on title length and word count)
            title_words = len(item.title.split()) if item.title else 0
            # Prefer titles with 5-15 words
            if 5 <= title_words <= 15:
                title_score = 1.0
            elif title_words < 5:
                title_score = title_words / 5.0
            else:
                title_score = max(0.5, 1.0 - (title_words - 15) / 20.0)
            breakdown["title"] = title_score

            # Source trust score
            trust = trust_scores.get(item.source_id, 0.5)
            breakdown["source_trust"] = trust

            # Compute weighted total
            total = (
                breakdown["recency"] * self._criteria.recency_weight
                + breakdown["quality"] * self._criteria.quality_weight
                + breakdown["length"] * self._criteria.length_weight
                + breakdown["title"] * self._criteria.title_weight
                + breakdown["source_trust"] * self._criteria.source_trust_weight
            )

            scored.append(ScoredItem(item=item, score=total, score_breakdown=breakdown))

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)

        logger.debug(
            f"Scored {len(items)} items, best score: {scored[0].score:.2f}"
            if scored else "No items to score"
        )

        return scored

    def select_top_n(
        self,
        items: Sequence[NormalizedItemDTO],
        n: int = 3,
        *,
        source_trust_scores: dict[int, float] | None = None,
    ) -> list[NormalizedItemDTO]:
        """Select top N representative items.

        Args:
            items: List of items to select from.
            n: Number of items to select.
            source_trust_scores: Optional mapping of source_id to trust score.

        Returns:
            List of top N items.
        """
        if not items:
            return []

        scored = self.score_items(items, source_trust_scores=source_trust_scores)
        return [s.item for s in scored[:n]]
