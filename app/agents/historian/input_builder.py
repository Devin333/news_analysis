"""Input builder for Historian Agent.

Constructs the input context for the Historian Agent from
various data sources.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from app.agents.historian.schemas import HistorianInput, TimelinePoint
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.memory import (
        TimelinePointDTO,
        TopicHistoryContextDTO,
        TopicMemoryDTO,
        TopicSnapshotDTO,
    )
    from app.contracts.dto.normalized_item import NormalizedItemDTO
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class HistorianInputBuilder:
    """Build input context for Historian Agent."""

    def __init__(self) -> None:
        """Initialize the builder."""
        pass

    def build(
        self,
        topic: "TopicReadDTO",
        history_context: "TopicHistoryContextDTO | None" = None,
        representative_item: "NormalizedItemDTO | None" = None,
        recent_items: list["NormalizedItemDTO"] | None = None,
        entity_names: list[str] | None = None,
    ) -> HistorianInput:
        """Build Historian input from topic and context.

        Args:
            topic: The topic to analyze.
            history_context: Historical context from retrieval.
            representative_item: Representative item for the topic.
            recent_items: Recent items for analysis.
            entity_names: Names of related entities.

        Returns:
            HistorianInput ready for the agent.
        """
        # Build timeline points
        timeline_points: list[TimelinePoint] = []
        if history_context and history_context.timeline:
            timeline_points = [
                self._convert_timeline_point(tp)
                for tp in history_context.timeline[:20]  # Limit to 20
            ]

        # Build snapshots
        snapshots: list[dict] = []
        if history_context and history_context.latest_snapshot:
            snapshots = [self._snapshot_to_dict(history_context.latest_snapshot)]

        # Build existing memory
        existing_memory = None
        if history_context and history_context.topic_memory:
            existing_memory = self._memory_to_dict(history_context.topic_memory)

        # Build recent items
        recent_items_data: list[dict] = []
        if recent_items:
            recent_items_data = [
                self._item_to_dict(item)
                for item in recent_items[:10]  # Limit to 10
            ]

        # Build related topic IDs
        related_topic_ids: list[int] = []
        if history_context:
            related_topic_ids = history_context.similar_past_topics[:5]

        return HistorianInput(
            topic_id=topic.id,
            topic_title=topic.title,
            topic_summary=topic.summary,
            board_type=topic.board_type,
            current_item_count=topic.item_count,
            current_source_count=topic.source_count,
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
            representative_item_title=representative_item.title if representative_item else None,
            representative_item_excerpt=representative_item.excerpt if representative_item else None,
            representative_item_url=representative_item.url if representative_item else None,
            existing_timeline=timeline_points,
            existing_snapshots=snapshots,
            existing_memory=existing_memory,
            related_topic_ids=related_topic_ids,
            entity_names=entity_names or [],
            recent_items=recent_items_data,
        )

    def build_prompt_context(self, input_data: HistorianInput) -> str:
        """Build prompt context string from input.

        Args:
            input_data: Historian input data.

        Returns:
            Formatted context string for the prompt.
        """
        lines = [
            "## Topic Information",
            f"- **Title**: {input_data.topic_title}",
            f"- **ID**: {input_data.topic_id}",
            f"- **Board Type**: {input_data.board_type or 'general'}",
        ]

        if input_data.topic_summary:
            lines.append(f"- **Summary**: {input_data.topic_summary}")

        lines.extend([
            "",
            "## Current Metrics",
            f"- **Item Count**: {input_data.current_item_count}",
            f"- **Source Count**: {input_data.current_source_count}",
            f"- **Heat Score**: {input_data.heat_score:.2f}",
            f"- **Trend Score**: {input_data.trend_score:.2f}",
        ])

        if input_data.representative_item_title:
            lines.extend([
                "",
                "## Representative Item",
                f"- **Title**: {input_data.representative_item_title}",
            ])
            if input_data.representative_item_excerpt:
                excerpt = input_data.representative_item_excerpt[:300]
                lines.append(f"- **Excerpt**: {excerpt}...")
            if input_data.representative_item_url:
                lines.append(f"- **URL**: {input_data.representative_item_url}")

        if input_data.existing_timeline:
            lines.extend([
                "",
                "## Timeline Events",
            ])
            for tp in input_data.existing_timeline[:10]:
                lines.append(
                    f"- [{tp.event_time.strftime('%Y-%m-%d')}] "
                    f"{tp.event_type}: {tp.title}"
                )

        if input_data.existing_memory:
            lines.extend([
                "",
                "## Existing Memory",
                f"- **Historical Status**: {input_data.existing_memory.get('historical_status', 'unknown')}",
                f"- **Current Stage**: {input_data.existing_memory.get('current_stage', 'unknown')}",
            ])
            if input_data.existing_memory.get('history_summary'):
                lines.append(f"- **Previous Summary**: {input_data.existing_memory['history_summary']}")

        if input_data.recent_items:
            lines.extend([
                "",
                "## Recent Items",
            ])
            for item in input_data.recent_items[:5]:
                lines.append(f"- {item.get('title', 'Untitled')}")

        if input_data.entity_names:
            lines.extend([
                "",
                "## Related Entities",
                f"- {', '.join(input_data.entity_names[:10])}",
            ])

        return "\n".join(lines)

    def _convert_timeline_point(
        self,
        tp: "TimelinePointDTO",
    ) -> TimelinePoint:
        """Convert TimelinePointDTO to TimelinePoint."""
        return TimelinePoint(
            event_time=tp.event_time,
            event_type=tp.event_type,
            title=tp.title,
            description=tp.description,
            importance=tp.importance_score,
        )

    def _snapshot_to_dict(self, snapshot: "TopicSnapshotDTO") -> dict:
        """Convert snapshot to dict for input."""
        return {
            "snapshot_at": snapshot.snapshot_at.isoformat(),
            "summary": snapshot.summary,
            "why_it_matters": snapshot.why_it_matters,
            "system_judgement": snapshot.system_judgement,
            "heat_score": snapshot.heat_score,
            "item_count": snapshot.item_count,
        }

    def _memory_to_dict(self, memory: "TopicMemoryDTO") -> dict:
        """Convert memory to dict for input."""
        return {
            "first_seen_at": memory.first_seen_at.isoformat(),
            "last_seen_at": memory.last_seen_at.isoformat(),
            "historical_status": memory.historical_status,
            "current_stage": memory.current_stage,
            "history_summary": memory.history_summary,
            "key_milestones": memory.key_milestones,
        }

    def _item_to_dict(self, item: "NormalizedItemDTO") -> dict:
        """Convert item to dict for input."""
        return {
            "id": item.id,
            "title": item.title,
            "excerpt": item.excerpt[:200] if item.excerpt else None,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "content_type": item.content_type,
            "url": item.url,
        }
