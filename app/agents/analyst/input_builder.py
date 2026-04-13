"""Input builder for Analyst Agent.

Constructs the input context for the Analyst Agent from
various data sources.
"""

from typing import TYPE_CHECKING, Any

from app.agents.analyst.schemas import AnalystInput
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.agents.historian.schemas import HistorianOutput
    from app.contracts.dto.normalized_item import NormalizedItemDTO
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class AnalystInputBuilder:
    """Build input context for Analyst Agent."""

    def __init__(self) -> None:
        """Initialize the builder."""
        pass

    def build(
        self,
        topic: "TopicReadDTO",
        historian_output: "HistorianOutput | None" = None,
        representative_item: "NormalizedItemDTO | None" = None,
        recent_items: list["NormalizedItemDTO"] | None = None,
        tags: list[str] | None = None,
        entity_names: list[str] | None = None,
        recent_judgements: list[dict[str, Any]] | None = None,
    ) -> AnalystInput:
        """Build Analyst input from topic and context.

        Args:
            topic: The topic to analyze.
            historian_output: Optional historian output.
            representative_item: Representative item for the topic.
            recent_items: Recent items for analysis.
            tags: Topic tags.
            entity_names: Names of related entities.
            recent_judgements: Recent judgements for context.

        Returns:
            AnalystInput ready for the agent.
        """
        # Build recent items data
        recent_items_data: list[dict] = []
        if recent_items:
            recent_items_data = [
                self._item_to_dict(item)
                for item in recent_items[:10]
            ]

        # Build historian context
        historical_status = None
        current_stage = None
        history_summary = None
        what_is_new = None

        if historian_output:
            historical_status = historian_output.historical_status.value
            current_stage = historian_output.current_stage.value
            history_summary = historian_output.history_summary
            what_is_new = historian_output.what_is_new_this_time

        return AnalystInput(
            topic_id=topic.id,
            topic_title=topic.title,
            topic_summary=topic.summary,
            board_type=str(topic.board_type) if topic.board_type else None,
            item_count=topic.item_count,
            source_count=topic.source_count,
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
            representative_item_title=representative_item.title if representative_item else None,
            representative_item_excerpt=representative_item.excerpt if representative_item else None,
            tags=tags or [],
            historical_status=historical_status,
            current_stage=current_stage,
            history_summary=history_summary,
            what_is_new_this_time=what_is_new,
            recent_items=recent_items_data,
            entity_names=entity_names or [],
            recent_judgements=recent_judgements or [],
        )

    def build_prompt_context(self, input_data: AnalystInput) -> str:
        """Build prompt context string from input.

        Args:
            input_data: Analyst input data.

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
            f"- **Item Count**: {input_data.item_count}",
            f"- **Source Count**: {input_data.source_count}",
            f"- **Heat Score**: {input_data.heat_score:.2f}",
            f"- **Trend Score**: {input_data.trend_score:.2f}",
        ])

        if input_data.tags:
            lines.extend([
                "",
                "## Tags",
                f"- {', '.join(input_data.tags[:15])}",
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

        # Historical context from Historian
        if input_data.historical_status:
            lines.extend([
                "",
                "## Historical Context (from Historian)",
                f"- **Historical Status**: {input_data.historical_status}",
                f"- **Current Stage**: {input_data.current_stage or 'unknown'}",
            ])
            if input_data.history_summary:
                lines.append(f"- **History Summary**: {input_data.history_summary[:300]}...")
            if input_data.what_is_new_this_time:
                lines.append(f"- **What's New**: {input_data.what_is_new_this_time[:200]}...")

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

        if input_data.recent_judgements:
            lines.extend([
                "",
                "## Recent System Judgements",
            ])
            for j in input_data.recent_judgements[:3]:
                lines.append(
                    f"- [{j.get('agent_name', 'unknown')}] "
                    f"{j.get('judgement_type', 'unknown')}: "
                    f"{j.get('judgement', '')[:100]}"
                )

        return "\n".join(lines)

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
