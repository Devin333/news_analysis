"""Writer Agent input builder.

Constructs structured inputs for the Writer Agent based on
topic data, historian output, and analyst insights.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from app.agents.writer.schemas import CopyType, WriterInput
from app.bootstrap.logging import get_logger

if TYPE_CHECKING:
    from app.contracts.dto.topic import TopicReadDTO

logger = get_logger(__name__)


class WriterInputBuilder:
    """Builds inputs for the Writer Agent.

    Constructs different input structures based on the copy type.
    """

    def build_feed_card_input(
        self,
        topic: "TopicReadDTO",
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> WriterInput:
        """Build input for feed card generation.

        Args:
            topic: Topic data.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            representative_items: Optional representative items.
            tags: Optional tags.

        Returns:
            WriterInput configured for feed card.
        """
        return self._build_base_input(
            topic=topic,
            copy_type=CopyType.FEED_CARD,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
        )

    def build_topic_intro_input(
        self,
        topic: "TopicReadDTO",
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        timeline_points: list[dict[str, Any]] | None = None,
    ) -> WriterInput:
        """Build input for topic intro generation.

        Args:
            topic: Topic data.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            representative_items: Optional representative items.
            tags: Optional tags.
            timeline_points: Optional timeline points.

        Returns:
            WriterInput configured for topic intro.
        """
        input_data = self._build_base_input(
            topic=topic,
            copy_type=CopyType.TOPIC_INTRO,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
        )

        # Add timeline for topic intro
        if timeline_points:
            input_data.timeline_points = timeline_points[:10]  # Limit to 10

        return input_data

    def build_trend_card_input(
        self,
        topic: "TopicReadDTO",
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        trend_signals: list[dict[str, Any]] | None = None,
    ) -> WriterInput:
        """Build input for trend card generation.

        Args:
            topic: Topic data.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            representative_items: Optional representative items.
            tags: Optional tags.
            trend_signals: Optional trend signals.

        Returns:
            WriterInput configured for trend card.
        """
        input_data = self._build_base_input(
            topic=topic,
            copy_type=CopyType.TREND_CARD,
            historian_output=historian_output,
            analyst_output=analyst_output,
            representative_items=representative_items,
            tags=tags,
        )

        # Add trend signals
        if trend_signals:
            input_data.additional_context["trend_signals"] = trend_signals

        return input_data

    def build_report_section_input(
        self,
        topics: list["TopicReadDTO"],
        *,
        section_theme: str = "General",
        report_type: str = "daily",
        report_date: datetime | None = None,
        topic_enrichments: dict[int, dict[str, Any]] | None = None,
    ) -> WriterInput:
        """Build input for report section generation.

        Args:
            topics: List of topics for this section.
            section_theme: Theme of the section.
            report_type: Type of report (daily/weekly).
            report_date: Date of the report.
            topic_enrichments: Dict of topic_id -> enrichment data.

        Returns:
            WriterInput configured for report section.
        """
        if not topics:
            raise ValueError("At least one topic is required for report section")

        # Use first topic as primary
        primary_topic = topics[0]
        topic_enrichments = topic_enrichments or {}

        # Build topics data for context
        topics_data = []
        for topic in topics:
            enrichment = topic_enrichments.get(topic.id, {})
            topics_data.append({
                "id": topic.id,
                "title": topic.title,
                "summary": topic.summary,
                "board_type": str(topic.board_type),
                "heat_score": float(topic.heat_score),
                "trend_score": float(topic.trend_score),
                "historian_output": enrichment.get("historian_output"),
                "analyst_output": enrichment.get("analyst_output"),
            })

        input_data = WriterInput(
            topic_id=primary_topic.id,
            copy_type=CopyType.REPORT_SECTION,
            topic_title=section_theme,
            topic_summary=f"Report section covering {len(topics)} topics",
            board_type=str(primary_topic.board_type),
            tags=[],
            item_count=sum(t.item_count for t in topics),
            source_count=sum(t.source_count for t in topics),
            additional_context={
                "section_theme": section_theme,
                "report_type": report_type,
                "report_date": (report_date or datetime.utcnow()).isoformat(),
                "topics": topics_data,
            },
        )

        return input_data

    def _build_base_input(
        self,
        topic: "TopicReadDTO",
        copy_type: CopyType,
        *,
        historian_output: dict[str, Any] | None = None,
        analyst_output: dict[str, Any] | None = None,
        representative_items: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> WriterInput:
        """Build base input structure.

        Args:
            topic: Topic data.
            copy_type: Type of copy to generate.
            historian_output: Optional historian output.
            analyst_output: Optional analyst output.
            representative_items: Optional representative items.
            tags: Optional tags.

        Returns:
            Base WriterInput.
        """
        input_data = WriterInput(
            topic_id=topic.id,
            copy_type=copy_type,
            topic_title=topic.title,
            topic_summary=topic.summary,
            board_type=str(topic.board_type),
            tags=tags or [],
            item_count=topic.item_count,
            source_count=topic.source_count,
            heat_score=float(topic.heat_score),
            trend_score=float(topic.trend_score),
        )

        # Add historian output
        if historian_output:
            input_data.historian_output = historian_output
            input_data.history_summary = historian_output.get("history_summary")
            input_data.first_seen_at = historian_output.get("first_seen_at")
            input_data.what_is_new_this_time = historian_output.get("what_is_new_this_time")
            input_data.historical_status = historian_output.get("historical_status")

        # Add analyst output
        if analyst_output:
            input_data.analyst_output = analyst_output
            input_data.why_it_matters = analyst_output.get("why_it_matters")
            input_data.system_judgement = analyst_output.get("system_judgement")
            input_data.likely_audience = analyst_output.get("likely_audience", [])
            input_data.follow_up_points = analyst_output.get("follow_up_points", [])
            input_data.trend_stage = analyst_output.get("trend_stage")

        # Add representative items
        if representative_items:
            input_data.representative_items = representative_items

        return input_data

    def build_prompt_context(self, writer_input: WriterInput) -> str:
        """Build prompt context string from WriterInput.

        Args:
            writer_input: The writer input.

        Returns:
            Formatted context string for the prompt.
        """
        lines = [
            f"Topic ID: {writer_input.topic_id}",
            f"Copy Type: {writer_input.copy_type.value}",
            f"Title: {writer_input.topic_title}",
        ]

        if writer_input.topic_summary:
            lines.append(f"Summary: {writer_input.topic_summary}")

        if writer_input.board_type:
            lines.append(f"Board: {writer_input.board_type}")

        if writer_input.tags:
            lines.append(f"Tags: {', '.join(writer_input.tags)}")

        lines.append("")
        lines.append("Metrics:")
        lines.append(f"  Items: {writer_input.item_count}")
        lines.append(f"  Sources: {writer_input.source_count}")
        lines.append(f"  Heat: {writer_input.heat_score:.2f}")
        lines.append(f"  Trend: {writer_input.trend_score:.2f}")

        # Historian context
        if writer_input.historian_output or writer_input.history_summary:
            lines.append("")
            lines.append("Historical Context:")
            if writer_input.historical_status:
                lines.append(f"  Status: {writer_input.historical_status}")
            if writer_input.first_seen_at:
                lines.append(f"  First Seen: {writer_input.first_seen_at}")
            if writer_input.history_summary:
                lines.append(f"  History: {writer_input.history_summary}")
            if writer_input.what_is_new_this_time:
                lines.append(f"  What's New: {writer_input.what_is_new_this_time}")

        # Analyst context
        if writer_input.analyst_output or writer_input.why_it_matters:
            lines.append("")
            lines.append("Analysis:")
            if writer_input.why_it_matters:
                lines.append(f"  Why It Matters: {writer_input.why_it_matters}")
            if writer_input.system_judgement:
                lines.append(f"  Judgement: {writer_input.system_judgement}")
            if writer_input.trend_stage:
                lines.append(f"  Trend Stage: {writer_input.trend_stage}")
            if writer_input.likely_audience:
                lines.append(f"  Audience: {', '.join(writer_input.likely_audience)}")

        # Representative items
        if writer_input.representative_items:
            lines.append("")
            lines.append("Representative Content:")
            for item in writer_input.representative_items[:3]:
                title = item.get("title", "Untitled")
                lines.append(f"  - {title}")

        # Timeline
        if writer_input.timeline_points:
            lines.append("")
            lines.append("Timeline:")
            for point in writer_input.timeline_points[:5]:
                time = point.get("event_time", "")
                title = point.get("title", "")
                lines.append(f"  - {time}: {title}")

        return "\n".join(lines)
