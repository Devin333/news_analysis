"""Candidate topic retriever for clustering.

This module provides functionality to find candidate topics
that a normalized item might belong to.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.bootstrap.logging import get_logger
from app.common.enums import BoardType
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicCandidateDTO, TopicReadDTO
from app.processing.clustering.features import (
    compute_recency_score,
    compute_tag_overlap_score,
    compute_title_overlap_score,
)
from app.storage.repositories.topic_repository import TopicRepository

logger = get_logger(__name__)


@dataclass
class CandidateConfig:
    """Configuration for candidate retrieval."""

    # Time window for candidate topics (days)
    lookback_days: int = 7

    # Maximum candidates to retrieve
    max_candidates: int = 50

    # Minimum score threshold for candidates
    min_score_threshold: float = 0.1

    # Feature weights for scoring
    title_weight: float = 0.4
    tag_weight: float = 0.25
    recency_weight: float = 0.2
    board_weight: float = 0.15


@dataclass
class CandidateResult:
    """Result of candidate retrieval."""

    candidates: list[TopicCandidateDTO] = field(default_factory=list)
    total_evaluated: int = 0
    retrieval_time_ms: float = 0.0


class CandidateRetriever:
    """Retrieves candidate topics for a normalized item.

    The retriever uses multiple signals to find relevant topics:
    - Board type matching
    - Title keyword overlap
    - Tag overlap
    - Time proximity
    """

    def __init__(
        self,
        topic_repo: TopicRepository,
        config: CandidateConfig | None = None,
    ) -> None:
        """Initialize the retriever.

        Args:
            topic_repo: Repository for topic operations.
            config: Configuration for retrieval behavior.
        """
        self._topic_repo = topic_repo
        self._config = config or CandidateConfig()

    async def find_candidates(
        self,
        item: NormalizedItemDTO,
        *,
        board_type: BoardType | None = None,
    ) -> CandidateResult:
        """Find candidate topics for an item.

        Args:
            item: The normalized item to find candidates for.
            board_type: Optional board type filter.

        Returns:
            CandidateResult with scored candidates.
        """
        import time

        start_time = time.perf_counter()

        # Determine board type
        effective_board = board_type or item.board_type_candidate or BoardType.GENERAL

        # Retrieve recent topics
        topics = await self._topic_repo.find_candidates(
            board_type=effective_board,
            days=self._config.lookback_days,
            limit=self._config.max_candidates * 2,  # Get more for filtering
        )

        logger.debug(f"Retrieved {len(topics)} candidate topics for evaluation")

        # Score each topic
        scored_candidates: list[TopicCandidateDTO] = []
        for topic in topics:
            candidate = self._score_candidate(item, topic)
            if candidate.similarity_score >= self._config.min_score_threshold:
                scored_candidates.append(candidate)

        # Sort by score descending
        scored_candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        # Limit results
        final_candidates = scored_candidates[: self._config.max_candidates]

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Found {len(final_candidates)} candidates for item '{item.title[:50]}...' "
            f"(evaluated {len(topics)}, took {elapsed_ms:.1f}ms)"
        )

        return CandidateResult(
            candidates=final_candidates,
            total_evaluated=len(topics),
            retrieval_time_ms=elapsed_ms,
        )

    def _score_candidate(
        self,
        item: NormalizedItemDTO,
        topic: TopicReadDTO,
    ) -> TopicCandidateDTO:
        """Score a candidate topic against an item.

        Args:
            item: The normalized item.
            topic: The candidate topic.

        Returns:
            Scored TopicCandidateDTO.
        """
        match_reasons: list[str] = []
        scores: dict[str, float] = {}

        # Title overlap
        title_score = compute_title_overlap_score(item.title, topic.title)
        scores["title"] = title_score
        if title_score > 0.3:
            match_reasons.append(f"title_overlap:{title_score:.2f}")

        # Tag overlap
        item_tags = item.tags or []
        # Topic tags would come from topic metadata or a separate query
        topic_tags = topic.metadata_json.get("tags", []) if topic.metadata_json else []
        tag_score = compute_tag_overlap_score(item_tags, topic_tags)
        scores["tag"] = tag_score
        if tag_score > 0.2:
            match_reasons.append(f"tag_overlap:{tag_score:.2f}")

        # Recency score
        recency_score = compute_recency_score(
            item.published_at,
            topic.last_seen_at,
            max_hours=self._config.lookback_days * 24,
        )
        scores["recency"] = recency_score
        if recency_score > 0.5:
            match_reasons.append(f"recent:{recency_score:.2f}")

        # Board type match (binary)
        board_match = 1.0 if item.board_type_candidate == topic.board_type else 0.0
        scores["board"] = board_match
        if board_match > 0:
            match_reasons.append("same_board")

        # Compute weighted total score
        total_score = (
            scores["title"] * self._config.title_weight
            + scores["tag"] * self._config.tag_weight
            + scores["recency"] * self._config.recency_weight
            + scores["board"] * self._config.board_weight
        )

        return TopicCandidateDTO(
            topic_id=topic.id,
            title=topic.title,
            board_type=topic.board_type,
            item_count=topic.item_count,
            last_seen_at=topic.last_seen_at,
            similarity_score=total_score,
            match_reasons=match_reasons,
        )

    async def find_candidates_multi_board(
        self,
        item: NormalizedItemDTO,
    ) -> CandidateResult:
        """Find candidates across all board types.

        Useful when board type is uncertain.

        Args:
            item: The normalized item.

        Returns:
            CandidateResult with candidates from all boards.
        """
        import time

        start_time = time.perf_counter()

        # Retrieve recent topics without board filter
        topics = await self._topic_repo.list_recent(
            limit=self._config.max_candidates * 2,
        )

        logger.debug(f"Retrieved {len(topics)} topics across all boards")

        # Score each topic
        scored_candidates: list[TopicCandidateDTO] = []
        for topic in topics:
            candidate = self._score_candidate(item, topic)
            if candidate.similarity_score >= self._config.min_score_threshold:
                scored_candidates.append(candidate)

        # Sort by score descending
        scored_candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        # Limit results
        final_candidates = scored_candidates[: self._config.max_candidates]

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return CandidateResult(
            candidates=final_candidates,
            total_evaluated=len(topics),
            retrieval_time_ms=elapsed_ms,
        )

    async def get_top_candidate(
        self,
        item: NormalizedItemDTO,
        *,
        min_score: float = 0.3,
    ) -> TopicCandidateDTO | None:
        """Get the best matching candidate topic.

        Args:
            item: The normalized item.
            min_score: Minimum score required.

        Returns:
            Best candidate or None if no good match.
        """
        result = await self.find_candidates(item)

        if not result.candidates:
            return None

        top = result.candidates[0]
        if top.similarity_score < min_score:
            return None

        return top
