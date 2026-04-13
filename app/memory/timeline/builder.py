"""Timeline Builder for constructing topic timelines.

Aggregates events from multiple sources, sorts, deduplicates,
and marks milestones.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.bootstrap.logging import get_logger
from app.contracts.dto.memory import TimelinePointDTO, TopicSnapshotDTO
from app.memory.timeline.event_types import TimelineEventType, is_milestone_type
from app.memory.timeline.extractors import TimelineExtractor

if TYPE_CHECKING:
    from app.contracts.dto.normalized_item import NormalizedItemDTO
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class TimelineBuilder:
    """Build timelines for topics.

    Aggregates events from items, snapshots, and judgements,
    then sorts, deduplicates, and marks milestones.
    """

    def __init__(
        self,
        extractor: TimelineExtractor | None = None,
        *,
        dedup_window_minutes: int = 60,
        max_events: int = 100,
    ) -> None:
        """Initialize the builder.

        Args:
            extractor: Timeline extractor instance.
            dedup_window_minutes: Window for deduplicating similar events.
            max_events: Maximum events to include in timeline.
        """
        self._extractor = extractor or TimelineExtractor()
        self._dedup_window = timedelta(minutes=dedup_window_minutes)
        self._max_events = max_events

    def build_from_items(
        self,
        items: list["NormalizedItemDTO"],
        topic: "TopicReadDTO",
    ) -> list[TimelinePointDTO]:
        """Build timeline from normalized items.

        Args:
            items: List of normalized items.
            topic: The topic for context.

        Returns:
            Sorted list of TimelinePointDTO.
        """
        events: list[TimelinePointDTO] = []

        # Add first-seen event
        if topic.first_seen_at:
            first_seen = self._extractor.extract_first_seen_event(
                first_seen_at=topic.first_seen_at,
                title=topic.title,
                item_id=topic.representative_item_id,
            )
            events.append(first_seen)

        # Extract events from items
        for item in items:
            event = self._extractor.extract_from_normalized_item(item, topic.id)
            if event:
                events.append(event)

        # Sort and deduplicate
        events = self._sort_events(events)
        events = self._deduplicate_events(events)
        events = self._mark_milestones(events)

        return events[: self._max_events]

    def build_from_snapshots(
        self,
        snapshots: list[TopicSnapshotDTO],
    ) -> list[TimelinePointDTO]:
        """Build timeline from topic snapshots.

        Args:
            snapshots: List of topic snapshots.

        Returns:
            Sorted list of TimelinePointDTO.
        """
        events: list[TimelinePointDTO] = []

        for snapshot in snapshots:
            event = self._extractor.extract_from_topic_snapshot(snapshot)
            events.append(event)

        return self._sort_events(events)

    def build_combined(
        self,
        items: list["NormalizedItemDTO"],
        snapshots: list[TopicSnapshotDTO],
        topic: "TopicReadDTO",
    ) -> list[TimelinePointDTO]:
        """Build combined timeline from multiple sources.

        Args:
            items: List of normalized items.
            snapshots: List of topic snapshots.
            topic: The topic for context.

        Returns:
            Sorted, deduplicated list of TimelinePointDTO.
        """
        events: list[TimelinePointDTO] = []

        # Add first-seen event
        if topic.first_seen_at:
            first_seen = self._extractor.extract_first_seen_event(
                first_seen_at=topic.first_seen_at,
                title=topic.title,
                item_id=topic.representative_item_id,
            )
            events.append(first_seen)

        # Extract from items
        for item in items:
            event = self._extractor.extract_from_normalized_item(item, topic.id)
            if event:
                events.append(event)

        # Extract from snapshots (only significant ones)
        for snapshot in snapshots:
            if snapshot.system_judgement or snapshot.why_it_matters:
                event = self._extractor.extract_from_topic_snapshot(snapshot)
                events.append(event)

        # Add milestone events based on item count
        events.extend(self._generate_count_milestones(items, topic))

        # Sort, deduplicate, and mark milestones
        events = self._sort_events(events)
        events = self._deduplicate_events(events)
        events = self._mark_milestones(events)

        return events[: self._max_events]

    def merge_timelines(
        self,
        *timelines: list[TimelinePointDTO],
    ) -> list[TimelinePointDTO]:
        """Merge multiple timelines into one.

        Args:
            timelines: Variable number of timeline lists.

        Returns:
            Merged, sorted, deduplicated timeline.
        """
        all_events: list[TimelinePointDTO] = []
        for timeline in timelines:
            all_events.extend(timeline)

        events = self._sort_events(all_events)
        events = self._deduplicate_events(events)
        events = self._mark_milestones(events)

        return events[: self._max_events]

    def _sort_events(
        self,
        events: list[TimelinePointDTO],
    ) -> list[TimelinePointDTO]:
        """Sort events by time ascending."""
        return sorted(events, key=lambda e: e.event_time)

    def _deduplicate_events(
        self,
        events: list[TimelinePointDTO],
    ) -> list[TimelinePointDTO]:
        """Remove duplicate or very similar events.

        Events are considered duplicates if they:
        - Have the same event_type
        - Are within the dedup window
        - Have similar titles
        """
        if not events:
            return []

        result: list[TimelinePointDTO] = []
        seen: dict[str, datetime] = {}

        for event in events:
            # Create a key for deduplication
            key = f"{event.event_type}:{event.title[:50]}"

            # Check if we've seen a similar event recently
            if key in seen:
                last_time = seen[key]
                if abs((event.event_time - last_time).total_seconds()) < self._dedup_window.total_seconds():
                    # Skip duplicate
                    continue

            seen[key] = event.event_time
            result.append(event)

        return result

    def _mark_milestones(
        self,
        events: list[TimelinePointDTO],
    ) -> list[TimelinePointDTO]:
        """Mark milestone events based on type and importance."""
        result: list[TimelinePointDTO] = []

        for event in events:
            # Check if this event type is typically a milestone
            is_milestone = is_milestone_type(TimelineEventType(event.event_type))

            # Also mark high-importance events as milestones
            if event.importance_score >= 0.8:
                is_milestone = True

            # Update metadata with milestone flag
            metadata = dict(event.metadata)
            metadata["is_milestone"] = is_milestone

            result.append(
                TimelinePointDTO(
                    event_time=event.event_time,
                    event_type=event.event_type,
                    title=event.title,
                    description=event.description,
                    source_item_id=event.source_item_id,
                    source_type=event.source_type,
                    importance_score=event.importance_score,
                    metadata=metadata,
                )
            )

        return result

    def _generate_count_milestones(
        self,
        items: list["NormalizedItemDTO"],
        topic: "TopicReadDTO",
    ) -> list[TimelinePointDTO]:
        """Generate milestone events for item count thresholds."""
        events: list[TimelinePointDTO] = []
        milestones = [10, 25, 50, 100, 250, 500, 1000]

        # Sort items by published_at
        sorted_items = sorted(
            [i for i in items if i.published_at],
            key=lambda x: x.published_at,
        )

        current_count = 0
        for item in sorted_items:
            current_count += 1
            if current_count in milestones:
                event = self._extractor.extract_milestone_event(
                    event_time=item.published_at,
                    milestone_type="item_count",
                    value=current_count,
                    topic_title=topic.title,
                )
                events.append(event)

        return events
