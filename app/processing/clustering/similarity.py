"""Similarity computation for topic clustering.

This module provides functions to compute various similarity metrics
between items and topics for merge decision making.
"""

import math
from datetime import datetime, timezone
from typing import Sequence

from app.bootstrap.logging import get_logger
from app.contracts.protocols.embeddings import EmbeddingProviderProtocol
from app.processing.clustering.features import (
    compute_tag_overlap_score,
    compute_title_overlap_score,
    tokenize,
)

logger = get_logger(__name__)


def title_similarity(title1: str, title2: str) -> float:
    """Compute title similarity using Jaccard coefficient.

    Args:
        title1: First title.
        title2: Second title.

    Returns:
        Similarity score in range [0, 1].
    """
    return compute_title_overlap_score(title1, title2, min_overlap=1)


def summary_similarity(summary1: str | None, summary2: str | None) -> float:
    """Compute summary similarity using token overlap.

    Args:
        summary1: First summary.
        summary2: Second summary.

    Returns:
        Similarity score in range [0, 1].
    """
    if not summary1 or not summary2:
        return 0.0

    tokens1 = tokenize(summary1)
    tokens2 = tokenize(summary2)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


async def embedding_similarity(
    text1: str,
    text2: str,
    provider: EmbeddingProviderProtocol,
) -> float:
    """Compute embedding-based semantic similarity.

    Args:
        text1: First text.
        text2: Second text.
        provider: Embedding provider to use.

    Returns:
        Similarity score in range [0, 1].
    """
    if not text1 or not text2:
        return 0.0

    try:
        embeddings = await provider.embed_batch([text1, text2])
        emb1, emb2 = embeddings[0], embeddings[1]

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine = dot_product / (norm1 * norm2)
        # Normalize to [0, 1]
        return (cosine + 1) / 2

    except Exception as e:
        logger.warning(f"Embedding similarity failed: {e}")
        return 0.0


def time_overlap_score(
    time1: datetime | None,
    time2: datetime | None,
    *,
    max_hours: float = 168.0,  # 7 days
) -> float:
    """Compute time proximity score.

    Items closer in time get higher scores.

    Args:
        time1: First timestamp.
        time2: Second timestamp.
        max_hours: Maximum hours for non-zero score.

    Returns:
        Score in range [0, 1].
    """
    if time1 is None or time2 is None:
        return 0.5  # Neutral score

    # Ensure timezone-aware
    if time1.tzinfo is None:
        time1 = time1.replace(tzinfo=timezone.utc)
    if time2.tzinfo is None:
        time2 = time2.replace(tzinfo=timezone.utc)

    diff_hours = abs((time1 - time2).total_seconds()) / 3600.0

    if diff_hours >= max_hours:
        return 0.0

    return 1.0 - (diff_hours / max_hours)


def tag_similarity(tags1: Sequence[str], tags2: Sequence[str]) -> float:
    """Compute tag overlap similarity.

    Args:
        tags1: First tag list.
        tags2: Second tag list.

    Returns:
        Similarity score in range [0, 1].
    """
    return compute_tag_overlap_score(tags1, tags2)


def source_overlap_score(
    source_ids1: Sequence[int],
    source_ids2: Sequence[int],
) -> float:
    """Compute source overlap score.

    Args:
        source_ids1: First source ID list.
        source_ids2: Second source ID list.

    Returns:
        Similarity score in range [0, 1].
    """
    if not source_ids1 or not source_ids2:
        return 0.0

    set1 = set(source_ids1)
    set2 = set(source_ids2)

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union) if union else 0.0


def entity_overlap_score(
    entities1: Sequence[str],
    entities2: Sequence[str],
) -> float:
    """Compute entity overlap score.

    Args:
        entities1: First entity list.
        entities2: Second entity list.

    Returns:
        Similarity score in range [0, 1].
    """
    if not entities1 or not entities2:
        return 0.0

    set1 = set(e.lower() for e in entities1)
    set2 = set(e.lower() for e in entities2)

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union) if union else 0.0


def content_type_match(type1: str | None, type2: str | None) -> float:
    """Check if content types match.

    Args:
        type1: First content type.
        type2: Second content type.

    Returns:
        1.0 if match, 0.0 otherwise.
    """
    if not type1 or not type2:
        return 0.5  # Neutral

    return 1.0 if type1.lower() == type2.lower() else 0.0


def board_type_match(board1: str | None, board2: str | None) -> float:
    """Check if board types match.

    Args:
        board1: First board type.
        board2: Second board type.

    Returns:
        1.0 if match, 0.0 otherwise.
    """
    if not board1 or not board2:
        return 0.5  # Neutral

    return 1.0 if board1.lower() == board2.lower() else 0.0


class SimilarityCalculator:
    """Calculator for computing multiple similarity metrics."""

    def __init__(
        self,
        embedding_provider: EmbeddingProviderProtocol | None = None,
    ) -> None:
        """Initialize calculator.

        Args:
            embedding_provider: Optional embedding provider for semantic similarity.
        """
        self._embedding_provider = embedding_provider

    async def compute_all(
        self,
        *,
        title1: str,
        title2: str,
        summary1: str | None = None,
        summary2: str | None = None,
        tags1: Sequence[str] | None = None,
        tags2: Sequence[str] | None = None,
        time1: datetime | None = None,
        time2: datetime | None = None,
        source_ids1: Sequence[int] | None = None,
        source_ids2: Sequence[int] | None = None,
        entities1: Sequence[str] | None = None,
        entities2: Sequence[str] | None = None,
        use_embedding: bool = True,
    ) -> dict[str, float]:
        """Compute all similarity metrics.

        Args:
            title1, title2: Titles to compare.
            summary1, summary2: Summaries to compare.
            tags1, tags2: Tags to compare.
            time1, time2: Timestamps to compare.
            source_ids1, source_ids2: Source IDs to compare.
            entities1, entities2: Entities to compare.
            use_embedding: Whether to compute embedding similarity.

        Returns:
            Dictionary of similarity scores.
        """
        scores: dict[str, float] = {}

        # Title similarity
        scores["title"] = title_similarity(title1, title2)

        # Summary similarity
        scores["summary"] = summary_similarity(summary1, summary2)

        # Tag similarity
        scores["tags"] = tag_similarity(tags1 or [], tags2 or [])

        # Time overlap
        scores["time"] = time_overlap_score(time1, time2)

        # Source overlap
        scores["source"] = source_overlap_score(source_ids1 or [], source_ids2 or [])

        # Entity overlap
        scores["entity"] = entity_overlap_score(entities1 or [], entities2 or [])

        # Embedding similarity (if provider available and requested)
        if use_embedding and self._embedding_provider:
            # Use title + summary for embedding
            text1 = f"{title1} {summary1 or ''}"
            text2 = f"{title2} {summary2 or ''}"
            scores["embedding"] = await embedding_similarity(
                text1, text2, self._embedding_provider
            )
        else:
            scores["embedding"] = 0.0

        return scores
