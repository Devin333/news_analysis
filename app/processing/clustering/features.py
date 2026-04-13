"""Feature functions for topic clustering and candidate scoring.

This module provides functions to compute similarity and relevance scores
between normalized items and candidate topics.
"""

import re
from datetime import datetime, timezone
from typing import Sequence

from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase words.

    Args:
        text: Input text to tokenize.

    Returns:
        Set of lowercase word tokens.
    """
    if not text:
        return set()
    # Split on non-word characters, filter short tokens
    words = re.findall(r"\b\w{2,}\b", text.lower())
    return set(words)


def compute_title_overlap_score(
    item_title: str,
    topic_title: str,
    *,
    min_overlap: int = 2,
) -> float:
    """Compute title overlap score between item and topic.

    Uses Jaccard similarity on word tokens.

    Args:
        item_title: The item's title.
        topic_title: The topic's title.
        min_overlap: Minimum overlapping words required for non-zero score.

    Returns:
        Score between 0.0 and 1.0.
    """
    item_tokens = tokenize(item_title)
    topic_tokens = tokenize(topic_title)

    if not item_tokens or not topic_tokens:
        return 0.0

    intersection = item_tokens & topic_tokens
    if len(intersection) < min_overlap:
        return 0.0

    union = item_tokens | topic_tokens
    jaccard = len(intersection) / len(union)

    return jaccard


def compute_tag_overlap_score(
    item_tags: Sequence[str],
    topic_tags: Sequence[str],
) -> float:
    """Compute tag overlap score between item and topic.

    Args:
        item_tags: Tags associated with the item.
        topic_tags: Tags associated with the topic.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not item_tags or not topic_tags:
        return 0.0

    item_set = set(t.lower() for t in item_tags)
    topic_set = set(t.lower() for t in topic_tags)

    intersection = item_set & topic_set
    if not intersection:
        return 0.0

    # Use Jaccard similarity
    union = item_set | topic_set
    return len(intersection) / len(union)


def compute_recency_score(
    item_published_at: datetime | None,
    topic_last_seen_at: datetime,
    *,
    max_hours: float = 168.0,  # 7 days
) -> float:
    """Compute recency score based on time proximity.

    Items closer in time to the topic's last activity get higher scores.

    Args:
        item_published_at: When the item was published.
        topic_last_seen_at: When the topic was last updated.
        max_hours: Maximum hours difference for non-zero score.

    Returns:
        Score between 0.0 and 1.0.
    """
    if item_published_at is None:
        return 0.5  # Neutral score for unknown publish time

    # Ensure both are timezone-aware
    if item_published_at.tzinfo is None:
        item_published_at = item_published_at.replace(tzinfo=timezone.utc)
    if topic_last_seen_at.tzinfo is None:
        topic_last_seen_at = topic_last_seen_at.replace(tzinfo=timezone.utc)

    # Calculate time difference in hours
    diff = abs((item_published_at - topic_last_seen_at).total_seconds()) / 3600.0

    if diff >= max_hours:
        return 0.0

    # Linear decay
    return 1.0 - (diff / max_hours)


def compute_source_similarity(
    item_source_id: int | None,
    topic_source_ids: Sequence[int],
) -> float:
    """Compute source similarity score.

    Higher score if item comes from a source already in the topic.

    Args:
        item_source_id: The item's source ID.
        topic_source_ids: Source IDs of items in the topic.

    Returns:
        Score between 0.0 and 1.0.
    """
    if item_source_id is None or not topic_source_ids:
        return 0.0

    if item_source_id in topic_source_ids:
        return 1.0

    return 0.0


def compute_content_type_similarity(
    item_content_type: str | None,
    topic_content_types: Sequence[str],
) -> float:
    """Compute content type similarity score.

    Args:
        item_content_type: The item's content type.
        topic_content_types: Content types of items in the topic.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not item_content_type or not topic_content_types:
        return 0.5  # Neutral

    if item_content_type in topic_content_types:
        # Higher score if it's the dominant type
        count = topic_content_types.count(item_content_type)
        ratio = count / len(topic_content_types)
        return 0.5 + (ratio * 0.5)

    return 0.0


def extract_keywords(text: str, *, top_n: int = 10) -> list[str]:
    """Extract top keywords from text.

    Simple frequency-based extraction, filtering common stop words.

    Args:
        text: Input text.
        top_n: Number of top keywords to return.

    Returns:
        List of keywords.
    """
    # Common English stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "this", "that", "these", "those", "it", "its", "they", "them",
        "their", "we", "us", "our", "you", "your", "he", "him", "his",
        "she", "her", "who", "which", "what", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "not", "only", "same", "so", "than", "too",
        "very", "just", "also", "now", "new", "one", "two", "first",
        "over", "into", "out", "up", "down", "about", "after", "before",
    }

    tokens = tokenize(text)
    filtered = [t for t in tokens if t not in stop_words and len(t) > 2]

    # Count frequencies
    freq: dict[str, int] = {}
    for token in filtered:
        freq[token] = freq.get(token, 0) + 1

    # Sort by frequency
    sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_tokens[:top_n]]


def compute_keyword_overlap(
    item_text: str,
    topic_keywords: Sequence[str],
    *,
    top_n: int = 10,
) -> float:
    """Compute keyword overlap between item text and topic keywords.

    Args:
        item_text: The item's text content.
        topic_keywords: Keywords associated with the topic.
        top_n: Number of keywords to extract from item.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not item_text or not topic_keywords:
        return 0.0

    item_keywords = set(extract_keywords(item_text, top_n=top_n))
    topic_set = set(k.lower() for k in topic_keywords)

    if not item_keywords:
        return 0.0

    intersection = item_keywords & topic_set
    return len(intersection) / len(item_keywords)


def compute_entity_overlap(
    item_entities: Sequence[str],
    topic_entities: Sequence[str],
) -> float:
    """Compute entity overlap score.

    Placeholder for future NER-based entity matching.

    Args:
        item_entities: Entities extracted from item.
        topic_entities: Entities associated with topic.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not item_entities or not topic_entities:
        return 0.0

    item_set = set(e.lower() for e in item_entities)
    topic_set = set(e.lower() for e in topic_entities)

    intersection = item_set & topic_set
    if not intersection:
        return 0.0

    # Jaccard similarity
    union = item_set | topic_set
    return len(intersection) / len(union)
