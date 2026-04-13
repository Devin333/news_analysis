"""Merge scoring for topic clustering.

This module provides the merge scorer that combines multiple similarity
metrics into a final merge decision score.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from app.bootstrap.logging import get_logger
from app.contracts.dto.topic import TopicCandidateScoreDTO
from app.contracts.protocols.embeddings import EmbeddingProviderProtocol
from app.processing.clustering.similarity import SimilarityCalculator

logger = get_logger(__name__)


@dataclass
class MergeWeights:
    """Weights for merge score computation.

    Default weights are designed to be interpretable and sum to 1.0.
    """

    title: float = 0.25
    embedding: float = 0.25
    tags: float = 0.20
    time: float = 0.15
    source: float = 0.10
    entity: float = 0.05

    def __post_init__(self) -> None:
        """Validate weights sum to 1.0."""
        total = (
            self.title
            + self.embedding
            + self.tags
            + self.time
            + self.source
            + self.entity
        )
        if abs(total - 1.0) > 0.001:
            logger.warning(f"Merge weights sum to {total}, not 1.0")


@dataclass
class MergeScoreResult:
    """Result of merge score computation."""

    topic_id: int
    topic_title: str
    total_score: float
    component_scores: dict[str, float]
    should_merge: bool
    confidence: float
    rationale: str


@dataclass
class ItemContext:
    """Context for an item being evaluated for merge."""

    title: str
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    source_id: int | None = None
    entities: list[str] = field(default_factory=list)
    content_type: str | None = None
    board_type: str | None = None


@dataclass
class TopicContext:
    """Context for a topic being evaluated for merge."""

    topic_id: int
    title: str
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    last_seen_at: datetime | None = None
    source_ids: list[int] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    item_count: int = 0


class MergeScorer:
    """Scorer for topic merge decisions.

    Combines multiple similarity metrics with configurable weights
    to produce a final merge score and recommendation.
    """

    def __init__(
        self,
        weights: MergeWeights | None = None,
        embedding_provider: EmbeddingProviderProtocol | None = None,
        merge_threshold: float = 0.5,
        high_confidence_threshold: float = 0.7,
    ) -> None:
        """Initialize the scorer.

        Args:
            weights: Weights for score components.
            embedding_provider: Optional embedding provider.
            merge_threshold: Minimum score to recommend merge.
            high_confidence_threshold: Score for high confidence merge.
        """
        self._weights = weights or MergeWeights()
        self._similarity = SimilarityCalculator(embedding_provider)
        self._merge_threshold = merge_threshold
        self._high_confidence_threshold = high_confidence_threshold

    async def score_candidate(
        self,
        item: ItemContext,
        topic: TopicContext,
        *,
        use_embedding: bool = True,
    ) -> MergeScoreResult:
        """Score a single candidate topic for merge.

        Args:
            item: Item context.
            topic: Topic context.
            use_embedding: Whether to use embedding similarity.

        Returns:
            MergeScoreResult with score and recommendation.
        """
        # Compute all similarity metrics
        scores = await self._similarity.compute_all(
            title1=item.title,
            title2=topic.title,
            summary1=item.summary,
            summary2=topic.summary,
            tags1=item.tags,
            tags2=topic.tags,
            time1=item.published_at,
            time2=topic.last_seen_at,
            source_ids1=[item.source_id] if item.source_id else [],
            source_ids2=topic.source_ids,
            entities1=item.entities,
            entities2=topic.entities,
            use_embedding=use_embedding,
        )

        # Compute weighted total
        total_score = (
            scores["title"] * self._weights.title
            + scores["embedding"] * self._weights.embedding
            + scores["tags"] * self._weights.tags
            + scores["time"] * self._weights.time
            + scores["source"] * self._weights.source
            + scores["entity"] * self._weights.entity
        )

        # Determine merge recommendation
        should_merge = total_score >= self._merge_threshold

        # Compute confidence
        if total_score >= self._high_confidence_threshold:
            confidence = 0.9 + (total_score - self._high_confidence_threshold) * 0.3
        elif total_score >= self._merge_threshold:
            confidence = 0.6 + (total_score - self._merge_threshold) * 0.6
        else:
            confidence = total_score / self._merge_threshold * 0.5

        confidence = min(confidence, 1.0)

        # Build rationale
        rationale = self._build_rationale(scores, total_score, should_merge)

        return MergeScoreResult(
            topic_id=topic.topic_id,
            topic_title=topic.title,
            total_score=total_score,
            component_scores=scores,
            should_merge=should_merge,
            confidence=confidence,
            rationale=rationale,
        )

    async def score_candidates(
        self,
        item: ItemContext,
        topics: Sequence[TopicContext],
        *,
        use_embedding: bool = True,
    ) -> list[MergeScoreResult]:
        """Score multiple candidate topics.

        Args:
            item: Item context.
            topics: List of topic contexts.
            use_embedding: Whether to use embedding similarity.

        Returns:
            List of MergeScoreResults, sorted by score descending.
        """
        results: list[MergeScoreResult] = []

        for topic in topics:
            result = await self.score_candidate(
                item, topic, use_embedding=use_embedding
            )
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.total_score, reverse=True)

        return results

    async def find_best_merge(
        self,
        item: ItemContext,
        topics: Sequence[TopicContext],
        *,
        use_embedding: bool = True,
    ) -> MergeScoreResult | None:
        """Find the best topic to merge with.

        Args:
            item: Item context.
            topics: List of topic contexts.
            use_embedding: Whether to use embedding similarity.

        Returns:
            Best MergeScoreResult if merge recommended, None otherwise.
        """
        if not topics:
            return None

        results = await self.score_candidates(item, topics, use_embedding=use_embedding)

        if not results:
            return None

        best = results[0]
        if best.should_merge:
            return best

        return None

    def to_candidate_score_dto(self, result: MergeScoreResult) -> TopicCandidateScoreDTO:
        """Convert MergeScoreResult to TopicCandidateScoreDTO.

        Args:
            result: Merge score result.

        Returns:
            TopicCandidateScoreDTO.
        """
        return TopicCandidateScoreDTO(
            topic_id=result.topic_id,
            title=result.topic_title,
            total_score=result.total_score,
            title_similarity=result.component_scores.get("title", 0.0),
            tag_overlap=result.component_scores.get("tags", 0.0),
            recency_score=result.component_scores.get("time", 0.0),
            source_similarity=result.component_scores.get("source", 0.0),
            embedding_similarity=result.component_scores.get("embedding", 0.0),
            should_merge=result.should_merge,
            confidence=result.confidence,
        )

    def _build_rationale(
        self,
        scores: dict[str, float],
        total: float,
        should_merge: bool,
    ) -> str:
        """Build human-readable rationale for merge decision.

        Args:
            scores: Component scores.
            total: Total score.
            should_merge: Whether merge is recommended.

        Returns:
            Rationale string.
        """
        parts: list[str] = []

        # Identify strong signals
        strong_signals: list[str] = []
        weak_signals: list[str] = []

        for name, score in scores.items():
            if score >= 0.7:
                strong_signals.append(f"{name}={score:.2f}")
            elif score >= 0.3:
                weak_signals.append(f"{name}={score:.2f}")

        if should_merge:
            parts.append(f"Recommend merge (score={total:.2f})")
            if strong_signals:
                parts.append(f"Strong: {', '.join(strong_signals)}")
        else:
            parts.append(f"No merge (score={total:.2f})")
            if weak_signals:
                parts.append(f"Partial: {', '.join(weak_signals)}")

        return "; ".join(parts)
