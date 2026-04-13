"""Timeline event extractors.

Extract timeline events from various sources:
- Normalized items
- Topic snapshots
- Judgements
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TimelinePointDTO, TopicSnapshotDTO
from app.memory.timeline.event_types import (
    TimelineEventType,
    get_base_importance,
)

if TYPE_CHECKING:
    from app.contracts.dto.normalized_item import NormalizedItemDTO

logger = get_logger(__name__)


class TimelineExtractor:
    """Extract timeline events from various sources."""

    def extract_from_normalized_item(
        self,
        item: "NormalizedItemDTO",
        topic_id: int | None = None,
    ) -> TimelinePointDTO | None:
        """Extract a timeline event from a normalized item.

        Args:
            item: The normalized item.
            topic_id: Optional topic ID for context.

        Returns:
            TimelinePointDTO or None if not extractable.
        """
        if item.published_at is None:
            return None

        # Determine event type based on content type
        event_type = self._determine_item_event_type(item)
        importance = self._calculate_item_importance(item, event_type)

        return TimelinePointDTO(
            event_time=item.published_at,
            event_type=event_type,
            title=item.title[:200] if item.title else "Untitled",
            description=item.excerpt[:500] if item.excerpt else None,
            source_item_id=item.id,
            source_type="item",
            importance_score=importance,
            metadata={
                "content_type": item.content_type,
                "source_id": item.source_id,
                "url": item.url,
            },
        )

    def extract_from_topic_snapshot(
        self,
        snapshot: TopicSnapshotDTO,
    ) -> TimelinePointDTO:
        """Extract a timeline event from a topic snapshot.

        Args:
            snapshot: The topic snapshot.

        Returns:
            TimelinePointDTO.
        """
        # Determine if this is a significant snapshot
        event_type = TimelineEventType.SNAPSHOT_CREATED
        importance = 0.3

        # Check for significant changes
        if snapshot.system_judgement:
            event_type = TimelineEventType.ANALYST_JUDGEMENT
            importance = 0.55

        title = f"Topic snapshot at {snapshot.snapshot_at.strftime('%Y-%m-%d')}"
        if snapshot.summary:
            title = snapshot.summary[:100]

        return TimelinePointDTO(
            event_time=snapshot.snapshot_at,
            event_type=event_type,
            title=title,
            description=snapshot.why_it_matters,
            source_item_id=snapshot.representative_item_id,
            source_type="snapshot",
            importance_score=importance,
            metadata={
                "snapshot_id": snapshot.id,
                "heat_score": snapshot.heat_score,
                "item_count": snapshot.item_count,
            },
        )

    def extract_first_seen_event(
        self,
        first_seen_at: datetime,
        title: str,
        item_id: int | None = None,
    ) -> TimelinePointDTO:
        """Create a first-seen event.

        Args:
            first_seen_at: When the topic was first seen.
            title: Topic title.
            item_id: Optional source item ID.

        Returns:
            TimelinePointDTO.
        """
        return TimelinePointDTO(
            event_time=first_seen_at,
            event_type=TimelineEventType.FIRST_SEEN,
            title=f"首次出现: {title[:150]}",
            description=None,
            source_item_id=item_id,
            source_type="topic",
            importance_score=get_base_importance(TimelineEventType.FIRST_SEEN),
            metadata={},
        )

    def extract_release_event(
        self,
        item: "NormalizedItemDTO",
    ) -> TimelinePointDTO | None:
        """Extract a release event from an item.

        Args:
            item: The normalized item (should be a release).

        Returns:
            TimelinePointDTO or None.
        """
        if item.published_at is None:
            return None

        # Extract version from title if possible
        version = self._extract_version(item.title)
        title = f"版本发布: {item.title[:150]}"
        if version:
            title = f"版本 {version} 发布"

        return TimelinePointDTO(
            event_time=item.published_at,
            event_type=TimelineEventType.RELEASE_PUBLISHED,
            title=title,
            description=item.excerpt[:300] if item.excerpt else None,
            source_item_id=item.id,
            source_type="item",
            importance_score=get_base_importance(TimelineEventType.RELEASE_PUBLISHED),
            metadata={
                "version": version,
                "url": item.url,
            },
        )

    def extract_paper_event(
        self,
        item: "NormalizedItemDTO",
    ) -> TimelinePointDTO | None:
        """Extract a paper publication event.

        Args:
            item: The normalized item (should be a paper).

        Returns:
            TimelinePointDTO or None.
        """
        if item.published_at is None:
            return None

        return TimelinePointDTO(
            event_time=item.published_at,
            event_type=TimelineEventType.PAPER_PUBLISHED,
            title=f"论文发表: {item.title[:150]}",
            description=item.excerpt[:300] if item.excerpt else None,
            source_item_id=item.id,
            source_type="item",
            importance_score=get_base_importance(TimelineEventType.PAPER_PUBLISHED),
            metadata={
                "url": item.url,
                "authors": item.metadata_json.get("authors", []) if item.metadata_json else [],
            },
        )

    def extract_milestone_event(
        self,
        event_time: datetime,
        milestone_type: str,
        value: int | float,
        topic_title: str,
    ) -> TimelinePointDTO:
        """Create a milestone event.

        Args:
            event_time: When the milestone was reached.
            milestone_type: Type of milestone (item_count, source_count, etc.).
            value: The milestone value.
            topic_title: Topic title for context.

        Returns:
            TimelinePointDTO.
        """
        if milestone_type == "item_count":
            event_type = TimelineEventType.ITEM_COUNT_MILESTONE
            title = f"内容数量达到 {int(value)} 条"
        elif milestone_type == "source_count":
            event_type = TimelineEventType.SOURCE_COUNT_MILESTONE
            title = f"来源数量达到 {int(value)} 个"
        else:
            event_type = TimelineEventType.EXTERNAL_MILESTONE
            title = f"里程碑: {milestone_type} = {value}"

        return TimelinePointDTO(
            event_time=event_time,
            event_type=event_type,
            title=title,
            description=f"话题 '{topic_title[:50]}' {title}",
            source_item_id=None,
            source_type="milestone",
            importance_score=get_base_importance(event_type),
            metadata={
                "milestone_type": milestone_type,
                "value": value,
            },
        )

    def extract_status_change_event(
        self,
        event_time: datetime,
        old_status: str,
        new_status: str,
        topic_title: str,
    ) -> TimelinePointDTO:
        """Create a status change event.

        Args:
            event_time: When the status changed.
            old_status: Previous status.
            new_status: New status.
            topic_title: Topic title.

        Returns:
            TimelinePointDTO.
        """
        return TimelinePointDTO(
            event_time=event_time,
            event_type=TimelineEventType.STATUS_CHANGED,
            title=f"状态变更: {old_status} → {new_status}",
            description=f"话题 '{topic_title[:50]}' 状态从 {old_status} 变为 {new_status}",
            source_item_id=None,
            source_type="status",
            importance_score=get_base_importance(TimelineEventType.STATUS_CHANGED),
            metadata={
                "old_status": old_status,
                "new_status": new_status,
            },
        )

    def _determine_item_event_type(
        self,
        item: "NormalizedItemDTO",
    ) -> str:
        """Determine event type based on item content type."""
        content_type = item.content_type or ""

        if "release" in content_type.lower():
            return TimelineEventType.RELEASE_PUBLISHED
        elif "paper" in content_type.lower() or "arxiv" in (item.url or "").lower():
            return TimelineEventType.PAPER_PUBLISHED
        elif "repo" in content_type.lower() or "github" in (item.url or "").lower():
            return TimelineEventType.REPO_CREATED
        elif "news" in content_type.lower():
            return TimelineEventType.NEWS_PUBLISHED
        else:
            return TimelineEventType.ARTICLE_PUBLISHED

    def _calculate_item_importance(
        self,
        item: "NormalizedItemDTO",
        event_type: str,
    ) -> float:
        """Calculate importance score for an item event."""
        base = get_base_importance(TimelineEventType(event_type))

        # Adjust based on item properties
        adjustments = 0.0

        # Longer content might be more important
        if item.excerpt and len(item.excerpt) > 500:
            adjustments += 0.05

        # Has summary
        if item.summary:
            adjustments += 0.05

        return min(base + adjustments, 1.0)

    def _extract_version(self, title: str) -> str | None:
        """Extract version number from title."""
        import re

        # Common version patterns
        patterns = [
            r"v?(\d+\.\d+(?:\.\d+)?(?:-\w+)?)",
            r"version\s+(\d+\.\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
