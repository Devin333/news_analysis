"""ReportEditor service.

Provides high-level methods for report generation.
"""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from app.agents.report_editor.agent import ReportEditorAgent
from app.agents.report_editor.schemas import ReportEditorOutput, ReportType
from app.bootstrap.logging import get_logger
from app.contracts.dto.report import (
    ReportCreateDTO,
    ReportDTO,
    ReportSectionDTO,
    ReportTopicSummaryDTO,
)

if TYPE_CHECKING:
    from app.storage.uow import UnitOfWork

logger = get_logger(__name__)


class ReportEditorService:
    """Service for report generation.

    Provides methods for generating daily and weekly reports
    using the ReportEditorAgent.
    """

    def __init__(
        self,
        uow: "UnitOfWork | None" = None,
    ) -> None:
        """Initialize the service.

        Args:
            uow: Unit of work for database access.
        """
        self._uow = uow
        self._agent = ReportEditorAgent()

    async def generate_daily_report(
        self,
        date: datetime | None = None,
        *,
        max_topics: int = 15,
        save_to_db: bool = True,
    ) -> tuple[ReportDTO | None, dict[str, Any]]:
        """Generate a daily report.

        Args:
            date: Report date (defaults to today).
            max_topics: Maximum topics to include.
            save_to_db: Whether to save to database.

        Returns:
            Tuple of (ReportDTO or None, metadata).
        """
        if date is None:
            date = datetime.now(timezone.utc)

        logger.info(f"Generating daily report for {date.date()}")

        # Get topics
        topics = await self._get_top_topics(window_days=1, limit=max_topics)
        if not topics:
            logger.warning("No topics found for daily report")
            return None, {"error": "No topics found"}

        # Get trend signals
        trend_signals = await self._get_trend_signals(window_days=1)

        # Get previous report for continuity
        previous_report = await self._get_previous_daily_report(date)

        # Generate report using agent
        output, meta = await self._agent.generate_daily_report(
            date,
            topics,
            trend_signals=trend_signals,
            previous_report=previous_report,
        )

        if output is None:
            logger.warning("ReportEditorAgent returned no output")
            return None, meta or {}

        # Convert to DTO
        report_dto = self._output_to_dto(output, date, "daily")

        # Save to database
        if save_to_db and self._uow:
            saved = await self._save_report(report_dto, topics)
            if saved:
                report_dto = saved

        return report_dto, meta or {}

    async def generate_weekly_report(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        *,
        max_topics: int = 25,
        save_to_db: bool = True,
    ) -> tuple[ReportDTO | None, dict[str, Any]]:
        """Generate a weekly report.

        Args:
            start_date: Week start date.
            end_date: Week end date.
            max_topics: Maximum topics to include.
            save_to_db: Whether to save to database.

        Returns:
            Tuple of (ReportDTO or None, metadata).
        """
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        logger.info(f"Generating weekly report for {start_date.date()} to {end_date.date()}")

        # Get topics
        topics = await self._get_top_topics(window_days=7, limit=max_topics)
        if not topics:
            logger.warning("No topics found for weekly report")
            return None, {"error": "No topics found"}

        # Get trend signals
        trend_signals = await self._get_trend_signals(window_days=7)

        # Get daily reports from the week
        daily_reports = await self._get_daily_reports_for_week(start_date, end_date)

        # Get previous weekly report
        previous_weekly = await self._get_previous_weekly_report(start_date)

        # Generate report using agent
        output, meta = await self._agent.generate_weekly_report(
            start_date,
            end_date,
            topics,
            trend_signals=trend_signals,
            daily_reports=daily_reports,
            previous_weekly=previous_weekly,
        )

        if output is None:
            logger.warning("ReportEditorAgent returned no output")
            return None, meta or {}

        # Convert to DTO
        report_dto = self._output_to_dto(output, start_date, "weekly")

        # Save to database
        if save_to_db and self._uow:
            saved = await self._save_report(report_dto, topics)
            if saved:
                report_dto = saved

        return report_dto, meta or {}

    async def _get_top_topics(
        self,
        window_days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Get top topics for report."""
        if self._uow is None:
            return []

        topics_repo = getattr(self._uow, "topics", None)
        if topics_repo is None:
            return []

        # Get recent topics
        topics = await topics_repo.list_recent(limit=limit * 2)

        # Convert to dicts and score
        result = []
        for topic in topics:
            result.append({
                "id": topic.id,
                "title": topic.title,
                "summary": topic.summary,
                "board_type": str(topic.board_type),
                "heat_score": float(topic.heat_score),
                "trend_score": float(topic.trend_score),
                "item_count": topic.item_count,
                "source_count": topic.source_count,
                "tags": [],  # Would load from tag repo
            })

        # Sort by combined score
        result.sort(
            key=lambda x: x["heat_score"] / 100 + x["trend_score"],
            reverse=True,
        )

        return result[:limit]

    async def _get_trend_signals(
        self,
        window_days: int,
    ) -> list[dict[str, Any]]:
        """Get trend signals for report."""
        # Stub - would query trend_signals table
        return []

    async def _get_previous_daily_report(
        self,
        date: datetime,
    ) -> dict[str, Any] | None:
        """Get previous daily report."""
        if self._uow is None:
            return None

        reports_repo = getattr(self._uow, "reports", None)
        if reports_repo is None:
            return None

        prev_date = date - timedelta(days=1)
        report = await reports_repo.get_daily_by_date(prev_date)
        if report:
            return report.model_dump()
        return None

    async def _get_previous_weekly_report(
        self,
        start_date: datetime,
    ) -> dict[str, Any] | None:
        """Get previous weekly report."""
        if self._uow is None:
            return None

        reports_repo = getattr(self._uow, "reports", None)
        if reports_repo is None:
            return None

        prev_start = start_date - timedelta(days=7)
        week_key = prev_start.strftime("%Y-W%W")
        report = await reports_repo.get_weekly_by_key(week_key)
        if report:
            return report.model_dump()
        return None

    async def _get_daily_reports_for_week(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get daily reports for a week."""
        # Stub - would query reports table
        return []

    def _output_to_dto(
        self,
        output: ReportEditorOutput,
        date: datetime,
        report_type: str,
    ) -> ReportDTO:
        """Convert agent output to DTO."""
        sections = []
        for section in output.sections:
            sections.append(ReportSectionDTO(
                section_id=section.section_id,
                section_title=section.section_title,
                section_intro=section.section_intro,
                key_points=section.key_points,
                topic_summaries=[
                    ReportTopicSummaryDTO(
                        topic_id=0,  # Would need to map
                        title=h.get("title", ""),
                        summary=h.get("summary", ""),
                    )
                    for h in section.topic_highlights
                ],
                closing_note=section.closing_note,
            ))

        return ReportDTO(
            report_type=report_type,
            report_date=date,
            title=output.report_title,
            executive_summary=output.executive_summary,
            sections=sections,
            generated_at=output.generated_at,
            status="draft",
            metadata={
                "key_highlights": output.key_highlights,
                "editorial_conclusion": output.editorial_conclusion,
                "watch_next_week": output.watch_next_week,
                "confidence": output.confidence,
            },
        )

    async def _save_report(
        self,
        report_dto: ReportDTO,
        topics: list[dict[str, Any]],
    ) -> ReportDTO | None:
        """Save report to database."""
        if self._uow is None:
            return None

        reports_repo = getattr(self._uow, "reports", None)
        if reports_repo is None:
            return None

        create_dto = ReportCreateDTO(
            report_type=report_dto.report_type,
            report_date=report_dto.report_date,
            title=report_dto.title,
            executive_summary=report_dto.executive_summary,
            sections=report_dto.sections,
            topic_ids=[t["id"] for t in topics],
            metadata=report_dto.metadata,
        )

        model = await reports_repo.create(create_dto)
        return await reports_repo.get_by_id(model.id)
