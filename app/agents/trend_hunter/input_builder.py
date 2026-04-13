"""TrendHunter input builder.

Constructs inputs for the TrendHunter Agent.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.agents.trend_hunter.schemas import TrendHunterInput
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class TrendHunterInputBuilder:
    """Builds inputs for the TrendHunter Agent."""

    def build_input(
        self,
        topic: "TopicReadDTO",
        *,
        metrics: dict[str, Any] | None = None,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> TrendHunterInput:
        """Build input for trend analysis.

        Args:
            topic: Topic data.
            metrics: Trend metrics.
            historian_output: Historian output.
            analyst_output: Analyst output.
            tags: Topic tags.

        Returns:
            TrendHunterInput.
        """
        metrics = metrics or {}

        input_data = TrendHunterInput(
            topic_id=topic.id,
            topic_title=topic.title,
            topic_summary=topic.summary,
            board_type=str(topic.board_type),
            tags=tags or [],
            item_count=topic.item_count,
            source_count=topic.source_count,
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
            # Growth metrics
            item_count_7d=metrics.get("item_count_7d", 0),
            item_count_30d=metrics.get("item_count_30d", 0),
            source_count_7d=metrics.get("source_count_7d", 0),
            source_count_30d=metrics.get("source_count_30d", 0),
            growth_rate_7d=metrics.get("growth_rate_7d", 0.0),
            growth_rate_30d=metrics.get("growth_rate_30d", 0.0),
            # Recency
            last_item_at=metrics.get("last_item_at"),
            items_last_24h=metrics.get("items_last_24h", 0),
            items_last_7d=metrics.get("items_last_7d", 0),
            # Source diversity
            unique_sources_7d=metrics.get("unique_sources_7d", 0),
            source_diversity_score=metrics.get("source_diversity_score", 0.0),
            # Signals
            has_recent_release=metrics.get("has_recent_release", False),
            has_discussion_spike=metrics.get("has_discussion_spike", False),
            related_entity_activity=metrics.get("related_entity_activity", []),
        )

        # Add historian output
        if historian_output:
            input_data.historian_output = historian_output
            input_data.historical_status = historian_output.get("historical_status")
            input_data.first_seen_at = historian_output.get("first_seen_at")

        # Add analyst output
        if analyst_output:
            input_data.analyst_output = analyst_output
            input_data.why_it_matters = analyst_output.get("why_it_matters")
            input_data.system_judgement = analyst_output.get("system_judgement")

        return input_data

    def build_prompt_context(self, trend_input: TrendHunterInput) -> str:
        """Build prompt context string.

        Args:
            trend_input: The trend input.

        Returns:
            Formatted context string.
        """
        lines = [
            f"Topic: {trend_input.topic_title}",
            f"ID: {trend_input.topic_id}",
        ]

        if trend_input.topic_summary:
            lines.append(f"Summary: {trend_input.topic_summary}")

        if trend_input.board_type:
            lines.append(f"Board: {trend_input.board_type}")

        if trend_input.tags:
            lines.append(f"Tags: {', '.join(trend_input.tags)}")

        lines.append("")
        lines.append("=== Current Metrics ===")
        lines.append(f"Items: {trend_input.item_count}")
        lines.append(f"Sources: {trend_input.source_count}")
        lines.append(f"Heat Score: {trend_input.heat_score:.2f}")
        lines.append(f"Trend Score: {trend_input.trend_score:.2f}")

        lines.append("")
        lines.append("=== Growth Metrics ===")
        lines.append(f"Items (7d): {trend_input.item_count_7d}")
        lines.append(f"Items (30d): {trend_input.item_count_30d}")
        lines.append(f"Growth Rate (7d): {trend_input.growth_rate_7d:.1%}")
        lines.append(f"Growth Rate (30d): {trend_input.growth_rate_30d:.1%}")

        lines.append("")
        lines.append("=== Recency ===")
        lines.append(f"Items (24h): {trend_input.items_last_24h}")
        lines.append(f"Items (7d): {trend_input.items_last_7d}")
        if trend_input.last_item_at:
            lines.append(f"Last Item: {trend_input.last_item_at}")

        lines.append("")
        lines.append("=== Source Diversity ===")
        lines.append(f"Unique Sources (7d): {trend_input.unique_sources_7d}")
        lines.append(f"Diversity Score: {trend_input.source_diversity_score:.2f}")

        lines.append("")
        lines.append("=== Signals ===")
        lines.append(f"Recent Release: {'Yes' if trend_input.has_recent_release else 'No'}")
        lines.append(f"Discussion Spike: {'Yes' if trend_input.has_discussion_spike else 'No'}")
        if trend_input.related_entity_activity:
            lines.append(f"Entity Activity: {', '.join(trend_input.related_entity_activity)}")

        if trend_input.historian_output:
            lines.append("")
            lines.append("=== Historical Context ===")
            if trend_input.historical_status:
                lines.append(f"Status: {trend_input.historical_status}")
            if trend_input.first_seen_at:
                lines.append(f"First Seen: {trend_input.first_seen_at}")

        if trend_input.analyst_output:
            lines.append("")
            lines.append("=== Analysis ===")
            if trend_input.why_it_matters:
                lines.append(f"Why It Matters: {trend_input.why_it_matters}")
            if trend_input.system_judgement:
                lines.append(f"Judgement: {trend_input.system_judgement}")

        return "\n".join(lines)
