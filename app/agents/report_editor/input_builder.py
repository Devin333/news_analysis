"""ReportEditor input builder.

Constructs input for the ReportEditor Agent.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.agents.report_editor.schemas import (
    ReportEditorInput,
    ReportType,
    TopicSummaryInput,
    TrendSignalInput,
)
from app.bootstrap.logging import get_logger

logger = get_logger(__name__)


class ReportEditorInputBuilder:
    """Builds input for the ReportEditor Agent."""

    def __init__(self) -> None:
        """Initialize the builder."""
        pass

    def build_daily_input(
        self,
        date: datetime,
        *,
        topics: list[dict[str, Any]],
        trend_signals: list[dict[str, Any]] | None = None,
        insights: list[str] | None = None,
        previous_report: dict[str, Any] | None = None,
    ) -> ReportEditorInput:
        """Build input for a daily report.

        Args:
            date: Report date.
            topics: List of topic dicts.
            trend_signals: Optional trend signals.
            insights: Optional key insights.
            previous_report: Optional previous report for continuity.

        Returns:
            ReportEditorInput.
        """
        topic_inputs = [self._build_topic_summary(t) for t in topics]
        signal_inputs = [self._build_trend_signal(s) for s in (trend_signals or [])]

        # Extract releases and discussions
        releases = self._extract_releases(topics)
        discussions = self._extract_discussions(topics)

        # Previous report context
        prev_summary = None
        prev_watch = []
        if previous_report:
            prev_summary = previous_report.get("executive_summary")
            prev_watch = previous_report.get("watch_next_week", [])

        return ReportEditorInput(
            report_type=ReportType.DAILY,
            report_date=date,
            top_topics=topic_inputs,
            trend_signals=signal_inputs,
            key_insights=insights or [],
            important_releases=releases,
            important_discussions=discussions,
            previous_report_summary=prev_summary,
            previous_watch_items=prev_watch,
        )

    def build_weekly_input(
        self,
        start_date: datetime,
        end_date: datetime,
        *,
        topics: list[dict[str, Any]],
        trend_signals: list[dict[str, Any]] | None = None,
        insights: list[str] | None = None,
        daily_reports: list[dict[str, Any]] | None = None,
        previous_weekly: dict[str, Any] | None = None,
    ) -> ReportEditorInput:
        """Build input for a weekly report.

        Args:
            start_date: Week start date.
            end_date: Week end date.
            topics: List of topic dicts.
            trend_signals: Optional trend signals.
            insights: Optional key insights.
            daily_reports: Optional daily reports from the week.
            previous_weekly: Optional previous weekly report.

        Returns:
            ReportEditorInput.
        """
        topic_inputs = [self._build_topic_summary(t) for t in topics]
        signal_inputs = [self._build_trend_signal(s) for s in (trend_signals or [])]

        # Extract releases and discussions
        releases = self._extract_releases(topics)
        discussions = self._extract_discussions(topics)

        # Aggregate insights from daily reports
        if daily_reports:
            for daily in daily_reports:
                daily_insights = daily.get("key_highlights", [])
                insights = (insights or []) + daily_insights

        # Previous report context
        prev_summary = None
        prev_watch = []
        if previous_weekly:
            prev_summary = previous_weekly.get("executive_summary")
            prev_watch = previous_weekly.get("watch_next_week", [])

        return ReportEditorInput(
            report_type=ReportType.WEEKLY,
            report_date=start_date,
            week_start=start_date,
            week_end=end_date,
            top_topics=topic_inputs,
            trend_signals=signal_inputs,
            key_insights=insights or [],
            important_releases=releases,
            important_discussions=discussions,
            previous_report_summary=prev_summary,
            previous_watch_items=prev_watch,
        )

    def build_prompt_context(self, input_data: ReportEditorInput) -> str:
        """Build prompt context from input.

        Args:
            input_data: ReportEditorInput.

        Returns:
            Formatted context string.
        """
        lines = []

        # Report type and date
        lines.append(f"Report Type: {input_data.report_type.value}")
        lines.append(f"Report Date: {input_data.report_date.strftime('%Y-%m-%d')}")

        if input_data.week_start and input_data.week_end:
            lines.append(
                f"Week: {input_data.week_start.strftime('%Y-%m-%d')} to "
                f"{input_data.week_end.strftime('%Y-%m-%d')}"
            )

        lines.append("")

        # Top topics
        lines.append("## Top Topics")
        for i, topic in enumerate(input_data.top_topics[:15], 1):
            lines.append(f"\n### {i}. {topic.title}")
            if topic.summary:
                lines.append(f"Summary: {topic.summary}")
            if topic.why_it_matters:
                lines.append(f"Why it matters: {topic.why_it_matters}")
            lines.append(f"Heat: {topic.heat_score:.1f}, Trend: {topic.trend_score:.2f}")
            if topic.trend_stage:
                lines.append(f"Trend stage: {topic.trend_stage}")
            if topic.tags:
                lines.append(f"Tags: {', '.join(topic.tags[:5])}")

        # Trend signals
        if input_data.trend_signals:
            lines.append("\n## Trend Signals")
            for signal in input_data.trend_signals[:10]:
                lines.append(
                    f"- [{signal.signal_type}] {signal.description} "
                    f"(strength: {signal.strength:.2f})"
                )

        # Key insights
        if input_data.key_insights:
            lines.append("\n## Key Insights")
            for insight in input_data.key_insights[:10]:
                lines.append(f"- {insight}")

        # Important releases
        if input_data.important_releases:
            lines.append("\n## Important Releases")
            for release in input_data.important_releases[:5]:
                lines.append(f"- {release}")

        # Important discussions
        if input_data.important_discussions:
            lines.append("\n## Important Discussions")
            for discussion in input_data.important_discussions[:5]:
                lines.append(f"- {discussion}")

        # Previous report context
        if input_data.previous_report_summary:
            lines.append("\n## Previous Report Context")
            lines.append(input_data.previous_report_summary[:500])

        if input_data.previous_watch_items:
            lines.append("\n## Items to Follow Up")
            for item in input_data.previous_watch_items[:5]:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _build_topic_summary(self, topic: dict[str, Any]) -> TopicSummaryInput:
        """Build topic summary input."""
        return TopicSummaryInput(
            topic_id=topic.get("id", 0),
            title=topic.get("title", ""),
            summary=topic.get("summary"),
            why_it_matters=topic.get("why_it_matters"),
            trend_stage=topic.get("trend_stage"),
            heat_score=float(topic.get("heat_score", 0)),
            trend_score=float(topic.get("trend_score", 0)),
            item_count=topic.get("item_count", 0),
            source_count=topic.get("source_count", 0),
            board_type=topic.get("board_type"),
            tags=topic.get("tags", []),
        )

    def _build_trend_signal(self, signal: dict[str, Any]) -> TrendSignalInput:
        """Build trend signal input."""
        return TrendSignalInput(
            topic_id=signal.get("topic_id", 0),
            signal_type=signal.get("signal_type", "unknown"),
            strength=float(signal.get("strength", 0)),
            description=signal.get("description", ""),
        )

    def _extract_releases(self, topics: list[dict[str, Any]]) -> list[str]:
        """Extract release-related items from topics."""
        releases = []
        for topic in topics:
            content_type = topic.get("content_type", "")
            if content_type in ("release", "announcement", "launch"):
                releases.append(topic.get("title", ""))
            # Check tags
            tags = topic.get("tags", [])
            if any(t in ("release", "launch", "announcement") for t in tags):
                if topic.get("title") not in releases:
                    releases.append(topic.get("title", ""))
        return releases[:10]

    def _extract_discussions(self, topics: list[dict[str, Any]]) -> list[str]:
        """Extract discussion-related items from topics."""
        discussions = []
        for topic in topics:
            content_type = topic.get("content_type", "")
            if content_type in ("discussion", "debate", "controversy"):
                discussions.append(topic.get("title", ""))
        return discussions[:10]
