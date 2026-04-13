"""Topic tag aggregator for aggregating item tags to topic level.

This module provides functionality to aggregate tags from items
belonging to a topic into topic-level tags.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.bootstrap.logging import get_logger
from app.contracts.dto.tag import TagMatchDTO, TagType, TopicTagDTO

logger = get_logger(__name__)


@dataclass
class AggregatorConfig:
    """Configuration for topic tag aggregation."""

    # Minimum item count for a tag to be included
    min_item_count: int = 1

    # Minimum confidence threshold
    min_confidence: float = 0.5

    # Maximum tags per topic
    max_tags_per_topic: int = 30

    # Maximum tags per type
    max_tags_per_type: int = 10

    # Weight for high-trust source tags
    high_trust_weight: float = 1.5

    # Weight for recent item tags
    recency_weight: float = 1.2

    # Recency window in hours
    recency_hours: int = 24


@dataclass
class ItemTagInfo:
    """Information about a tag from an item."""

    tag_name: str
    tag_type: TagType
    confidence: float
    source_trust: float = 1.0
    published_at: datetime | None = None
    item_id: int | None = None


@dataclass
class AggregatedTag:
    """Aggregated tag with statistics."""

    tag_name: str
    tag_type: TagType
    item_count: int
    total_confidence: float
    avg_confidence: float
    weighted_score: float
    sources: set[int] = field(default_factory=set)


@dataclass
class AggregationResult:
    """Result of topic tag aggregation."""

    topic_id: int
    tags: list[TopicTagDTO] = field(default_factory=list)
    total_items_processed: int = 0
    total_tags_found: int = 0
    processing_time_ms: float = 0.0


class TopicTagAggregator:
    """Aggregates item tags to topic level.

    Strategies:
    - High frequency tags get priority
    - High trust source tags get weight boost
    - Recent item tags get slight boost
    """

    def __init__(self, config: AggregatorConfig | None = None) -> None:
        """Initialize the aggregator.

        Args:
            config: Configuration for aggregation behavior.
        """
        self._config = config or AggregatorConfig()

    def aggregate(
        self,
        topic_id: int,
        item_tags: list[list[ItemTagInfo]],
    ) -> AggregationResult:
        """Aggregate tags from multiple items.

        Args:
            topic_id: The topic ID.
            item_tags: List of tag lists, one per item.

        Returns:
            AggregationResult with aggregated topic tags.
        """
        import time

        start_time = time.perf_counter()

        # Flatten and group by (tag_type, tag_name)
        tag_groups: dict[tuple[TagType, str], list[ItemTagInfo]] = {}

        total_tags = 0
        for tags in item_tags:
            for tag in tags:
                total_tags += 1
                key = (tag.tag_type, tag.tag_name.lower())
                if key not in tag_groups:
                    tag_groups[key] = []
                tag_groups[key].append(tag)

        # Aggregate each group
        aggregated: list[AggregatedTag] = []
        now = datetime.now(timezone.utc)

        for (tag_type, tag_name_lower), tags in tag_groups.items():
            if len(tags) < self._config.min_item_count:
                continue

            # Calculate statistics
            item_count = len(tags)
            total_confidence = sum(t.confidence for t in tags)
            avg_confidence = total_confidence / item_count

            if avg_confidence < self._config.min_confidence:
                continue

            # Calculate weighted score
            weighted_score = self._calculate_weighted_score(tags, now)

            # Get display name from first tag
            display_name = tags[0].tag_name

            # Collect unique sources (item IDs)
            sources = {t.item_id for t in tags if t.item_id is not None}

            aggregated.append(
                AggregatedTag(
                    tag_name=display_name,
                    tag_type=tag_type,
                    item_count=item_count,
                    total_confidence=total_confidence,
                    avg_confidence=avg_confidence,
                    weighted_score=weighted_score,
                    sources=sources,
                )
            )

        # Sort by weighted score
        aggregated.sort(key=lambda t: t.weighted_score, reverse=True)

        # Limit by type and total
        final_tags = self._limit_tags(aggregated)

        # Convert to DTOs
        topic_tags = [
            TopicTagDTO(
                topic_id=topic_id,
                tag_id=0,  # Will be resolved by repository
                tag_name=t.tag_name,
                tag_type=t.tag_type,
                confidence=t.avg_confidence,
                item_count=t.item_count,
                source="aggregated",
            )
            for t in final_tags
        ]

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Aggregated {len(topic_tags)} tags for topic {topic_id} "
            f"from {len(item_tags)} items ({total_tags} total tags) "
            f"in {elapsed_ms:.1f}ms"
        )

        return AggregationResult(
            topic_id=topic_id,
            tags=topic_tags,
            total_items_processed=len(item_tags),
            total_tags_found=total_tags,
            processing_time_ms=elapsed_ms,
        )

    def _calculate_weighted_score(
        self,
        tags: list[ItemTagInfo],
        now: datetime,
    ) -> float:
        """Calculate weighted score for a tag group.

        Args:
            tags: List of tags with same name/type.
            now: Current time for recency calculation.

        Returns:
            Weighted score.
        """
        base_score = 0.0

        for tag in tags:
            tag_score = tag.confidence

            # Apply trust weight
            if tag.source_trust > 0.8:
                tag_score *= self._config.high_trust_weight

            # Apply recency weight
            if tag.published_at:
                hours_ago = (now - tag.published_at).total_seconds() / 3600
                if hours_ago <= self._config.recency_hours:
                    tag_score *= self._config.recency_weight

            base_score += tag_score

        return base_score

    def _limit_tags(self, tags: list[AggregatedTag]) -> list[AggregatedTag]:
        """Limit tags by type and total count.

        Args:
            tags: Sorted list of aggregated tags.

        Returns:
            Limited list of tags.
        """
        type_counts: dict[TagType, int] = {}
        result: list[AggregatedTag] = []

        for tag in tags:
            # Check type limit
            type_count = type_counts.get(tag.tag_type, 0)
            if type_count >= self._config.max_tags_per_type:
                continue

            # Check total limit
            if len(result) >= self._config.max_tags_per_topic:
                break

            result.append(tag)
            type_counts[tag.tag_type] = type_count + 1

        return result

    def aggregate_from_matches(
        self,
        topic_id: int,
        item_matches: list[tuple[int, list[TagMatchDTO]]],
        *,
        source_trusts: dict[int, float] | None = None,
        published_times: dict[int, datetime] | None = None,
    ) -> AggregationResult:
        """Aggregate from TagMatchDTO lists.

        Convenience method for aggregating from tag service results.

        Args:
            topic_id: The topic ID.
            item_matches: List of (item_id, matches) tuples.
            source_trusts: Optional mapping of item_id to trust score.
            published_times: Optional mapping of item_id to published time.

        Returns:
            AggregationResult.
        """
        source_trusts = source_trusts or {}
        published_times = published_times or {}

        item_tags: list[list[ItemTagInfo]] = []

        for item_id, matches in item_matches:
            tags = [
                ItemTagInfo(
                    tag_name=m.tag_name,
                    tag_type=m.tag_type,
                    confidence=m.confidence,
                    source_trust=source_trusts.get(item_id, 1.0),
                    published_at=published_times.get(item_id),
                    item_id=item_id,
                )
                for m in matches
            ]
            item_tags.append(tags)

        return self.aggregate(topic_id, item_tags)

    def merge_topic_tags(
        self,
        existing_tags: list[TopicTagDTO],
        new_tags: list[TopicTagDTO],
    ) -> list[TopicTagDTO]:
        """Merge existing topic tags with new tags.

        Args:
            existing_tags: Current topic tags.
            new_tags: New tags to merge.

        Returns:
            Merged tag list.
        """
        # Index existing by (type, name)
        merged: dict[tuple[TagType, str], TopicTagDTO] = {}

        for tag in existing_tags:
            key = (tag.tag_type, tag.tag_name.lower())
            merged[key] = tag

        # Merge new tags
        for tag in new_tags:
            key = (tag.tag_type, tag.tag_name.lower())
            existing = merged.get(key)

            if existing:
                # Update counts and confidence
                merged[key] = TopicTagDTO(
                    topic_id=tag.topic_id,
                    tag_id=existing.tag_id or tag.tag_id,
                    tag_name=tag.tag_name,
                    tag_type=tag.tag_type,
                    confidence=max(existing.confidence, tag.confidence),
                    item_count=existing.item_count + tag.item_count,
                    source="aggregated",
                )
            else:
                merged[key] = tag

        # Sort by item count and confidence
        result = list(merged.values())
        result.sort(key=lambda t: (t.item_count, t.confidence), reverse=True)

        # Limit total
        return result[: self._config.max_tags_per_topic]


# Singleton instance
_default_aggregator: TopicTagAggregator | None = None


def get_topic_tag_aggregator() -> TopicTagAggregator:
    """Get the default topic tag aggregator.

    Returns:
        The default TopicTagAggregator instance.
    """
    global _default_aggregator
    if _default_aggregator is None:
        _default_aggregator = TopicTagAggregator()
    return _default_aggregator
