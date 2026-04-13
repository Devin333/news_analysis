"""Topic stub builder for basic topic summaries.

This module provides functionality to build basic topic summaries
without requiring LLM processing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from app.bootstrap.logging import get_logger
from app.contracts.dto.normalized_item import NormalizedItemDTO
from app.contracts.dto.topic import TopicReadDTO
from app.editorial.summary_builders.representative_item_selector import (
    RepresentativeItemSelector,
)

logger = get_logger(__name__)


@dataclass
class TopicStub:
    """A basic topic summary stub."""

    title: str
    summary: str
    item_count: int
    source_count: int
    time_range: str
    representative_item_id: int | None
    key_sources: list[str] = field(default_factory=list)
    common_tags: list[str] = field(default_factory=list)


class TopicStubBuilder:
    """Builds basic topic summary stubs.

    Creates summaries based on:
    - Topic title
    - Item count and source diversity
    - Time range of items
    - Common tags/keywords
    - Representative item
    """

    def __init__(
        self,
        item_selector: RepresentativeItemSelector | None = None,
    ) -> None:
        """Initialize the builder.

        Args:
            item_selector: Selector for representative items.
        """
        self._selector = item_selector or RepresentativeItemSelector()

    def build(
        self,
        topic: TopicReadDTO,
        items: Sequence[NormalizedItemDTO],
        *,
        source_names: dict[int, str] | None = None,
    ) -> TopicStub:
        """Build a topic stub from topic and items.

        Args:
            topic: The topic to summarize.
            items: Items belonging to the topic.
            source_names: Optional mapping of source_id to source name.

        Returns:
            TopicStub with summary information.
        """
        # Select representative item
        representative = self._selector.select(items) if items else None
        representative_id = representative.id if representative else topic.representative_item_id

        # Calculate time range
        time_range = self._calculate_time_range(items)

        # Extract common tags
        common_tags = self._extract_common_tags(items, top_n=5)

        # Get key sources
        key_sources = self._get_key_sources(items, source_names or {}, top_n=3)

        # Build summary text
        summary = self._build_summary_text(
            topic=topic,
            item_count=len(items),
            source_count=topic.source_count,
            time_range=time_range,
            key_sources=key_sources,
        )

        return TopicStub(
            title=topic.title,
            summary=summary,
            item_count=len(items) if items else topic.item_count,
            source_count=topic.source_count,
            time_range=time_range,
            representative_item_id=representative_id,
            key_sources=key_sources,
            common_tags=common_tags,
        )

    def build_from_items_only(
        self,
        items: Sequence[NormalizedItemDTO],
        *,
        source_names: dict[int, str] | None = None,
    ) -> TopicStub:
        """Build a topic stub from items only (no existing topic).

        Useful for previewing a potential topic before creation.

        Args:
            items: Items to summarize.
            source_names: Optional mapping of source_id to source name.

        Returns:
            TopicStub with summary information.
        """
        if not items:
            return TopicStub(
                title="Empty Topic",
                summary="No items",
                item_count=0,
                source_count=0,
                time_range="",
                representative_item_id=None,
            )

        # Use first item's title as topic title
        representative = self._selector.select(items)
        title = representative.title if representative else items[0].title

        # Count unique sources
        source_ids = set(i.source_id for i in items)
        source_count = len(source_ids)

        # Calculate time range
        time_range = self._calculate_time_range(items)

        # Extract common tags
        common_tags = self._extract_common_tags(items, top_n=5)

        # Get key sources
        key_sources = self._get_key_sources(items, source_names or {}, top_n=3)

        # Build summary
        summary = self._build_summary_text_simple(
            title=title,
            item_count=len(items),
            source_count=source_count,
            time_range=time_range,
        )

        return TopicStub(
            title=title,
            summary=summary,
            item_count=len(items),
            source_count=source_count,
            time_range=time_range,
            representative_item_id=representative.id if representative else None,
            key_sources=key_sources,
            common_tags=common_tags,
        )

    def _calculate_time_range(
        self,
        items: Sequence[NormalizedItemDTO],
    ) -> str:
        """Calculate human-readable time range of items."""
        if not items:
            return ""

        timestamps = [i.published_at for i in items if i.published_at]
        if not timestamps:
            return ""

        min_time = min(timestamps)
        max_time = max(timestamps)

        # Calculate duration
        duration = max_time - min_time
        hours = duration.total_seconds() / 3600

        if hours < 1:
            return "过去1小时内"
        elif hours < 24:
            return f"过去{int(hours)}小时内"
        elif hours < 24 * 7:
            days = int(hours / 24)
            return f"过去{days}天内"
        else:
            weeks = int(hours / (24 * 7))
            return f"过去{weeks}周内"

    def _extract_common_tags(
        self,
        items: Sequence[NormalizedItemDTO],
        top_n: int = 5,
    ) -> list[str]:
        """Extract most common tags from items."""
        tag_counts: dict[str, int] = {}

        for item in items:
            for tag in item.tags or []:
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

        # Sort by count and return top N
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:top_n]]

    def _get_key_sources(
        self,
        items: Sequence[NormalizedItemDTO],
        source_names: dict[int, str],
        top_n: int = 3,
    ) -> list[str]:
        """Get key source names."""
        source_counts: dict[int, int] = {}

        for item in items:
            source_counts[item.source_id] = source_counts.get(item.source_id, 0) + 1

        # Sort by count
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)

        # Get names
        key_sources: list[str] = []
        for source_id, _ in sorted_sources[:top_n]:
            name = source_names.get(source_id, f"Source {source_id}")
            key_sources.append(name)

        return key_sources

    def _build_summary_text(
        self,
        topic: TopicReadDTO,
        item_count: int,
        source_count: int,
        time_range: str,
        key_sources: list[str],
    ) -> str:
        """Build summary text for a topic."""
        parts: list[str] = [topic.title]

        # Add item/source info
        if item_count > 1:
            parts.append(f"（{item_count}条相关内容")
            if source_count > 1:
                parts.append(f"，来自{source_count}个来源）")
            else:
                parts.append("）")

        # Add time range
        if time_range:
            parts.append(f" {time_range}")

        # Add key sources
        if key_sources:
            parts.append(f"。主要来源：{', '.join(key_sources[:2])}")

        return "".join(parts)

    def _build_summary_text_simple(
        self,
        title: str,
        item_count: int,
        source_count: int,
        time_range: str,
    ) -> str:
        """Build simple summary text."""
        parts: list[str] = [title]

        if item_count > 1:
            parts.append(f"（{item_count}条内容")
            if source_count > 1:
                parts.append(f"，{source_count}个来源）")
            else:
                parts.append("）")

        if time_range:
            parts.append(f" {time_range}")

        return "".join(parts)
