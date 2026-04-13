"""Report repository for database operations."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap.logging import get_logger
from app.contracts.dto.report import ReportCreateDTO, ReportDTO, ReportSectionDTO
from app.storage.db.models.report import Report
from app.storage.db.models.report_topic_link import ReportTopicLink

logger = get_logger(__name__)


class ReportRepository:
    """Repository for Report operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Database session.
        """
        self._session = session

    async def create(self, dto: ReportCreateDTO) -> Report:
        """Create a new report.

        Args:
            dto: Report creation DTO.

        Returns:
            Created Report model.
        """
        model = Report(
            report_type=dto.report_type,
            report_date=dto.report_date,
            title=dto.title,
            executive_summary=dto.executive_summary,
            sections_json=[s.model_dump() for s in dto.sections],
            topic_count=len(dto.topic_ids),
            metadata_json=dto.metadata,
        )

        # Set week key for weekly reports
        if dto.report_type == "weekly":
            model.week_key = dto.report_date.strftime("%Y-W%W")

        self._session.add(model)
        await self._session.flush()

        # Create topic links
        for i, topic_id in enumerate(dto.topic_ids):
            link = ReportTopicLink(
                report_id=model.id,
                topic_id=topic_id,
                position=i,
                role="main",
            )
            self._session.add(link)

        await self._session.flush()
        logger.info(f"Created report {model.id} ({dto.report_type})")
        return model

    async def get_by_id(self, report_id: int) -> ReportDTO | None:
        """Get report by ID.

        Args:
            report_id: Report ID.

        Returns:
            ReportDTO or None.
        """
        stmt = select(Report).where(Report.id == report_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dto(model)

    async def get_daily_by_date(self, date: datetime) -> ReportDTO | None:
        """Get daily report by date.

        Args:
            date: Report date.

        Returns:
            ReportDTO or None.
        """
        # Normalize to start of day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59)

        stmt = (
            select(Report)
            .where(Report.report_type == "daily")
            .where(Report.report_date >= start_of_day)
            .where(Report.report_date <= end_of_day)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dto(model)

    async def get_weekly_by_key(self, week_key: str) -> ReportDTO | None:
        """Get weekly report by week key.

        Args:
            week_key: Week key (e.g., "2026-W15").

        Returns:
            ReportDTO or None.
        """
        stmt = (
            select(Report)
            .where(Report.report_type == "weekly")
            .where(Report.week_key == week_key)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_dto(model)

    async def list_recent(
        self,
        *,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[ReportDTO]:
        """List recent reports.

        Args:
            report_type: Optional filter by type.
            limit: Maximum reports.

        Returns:
            List of ReportDTOs.
        """
        stmt = select(Report).order_by(Report.report_date.desc()).limit(limit)

        if report_type:
            stmt = stmt.where(Report.report_type == report_type)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_dto(m) for m in models]

    async def update_status(
        self,
        report_id: int,
        status: str,
        *,
        review_status: str | None = None,
    ) -> Report | None:
        """Update report status.

        Args:
            report_id: Report ID.
            status: New status.
            review_status: Optional review status.

        Returns:
            Updated Report or None.
        """
        stmt = select(Report).where(Report.id == report_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        model.status = status
        if review_status:
            model.review_status = review_status
            model.reviewed_at = datetime.now(timezone.utc)

        if status == "published":
            model.published_at = datetime.now(timezone.utc)

        await self._session.flush()
        return model

    async def get_report_topics(self, report_id: int) -> list[int]:
        """Get topic IDs for a report.

        Args:
            report_id: Report ID.

        Returns:
            List of topic IDs.
        """
        stmt = (
            select(ReportTopicLink.topic_id)
            .where(ReportTopicLink.report_id == report_id)
            .order_by(ReportTopicLink.position)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_topic_to_report(
        self,
        report_id: int,
        topic_id: int,
        *,
        section_id: str | None = None,
        position: int = 0,
        role: str = "main",
        inclusion_reason: str | None = None,
        heat_score: float = 0.0,
        trend_score: float = 0.0,
    ) -> ReportTopicLink:
        """Add a topic to a report.

        Args:
            report_id: Report ID.
            topic_id: Topic ID.
            section_id: Optional section ID.
            position: Position in section.
            role: Role in report.
            inclusion_reason: Why included.
            heat_score: Topic heat score.
            trend_score: Topic trend score.

        Returns:
            Created ReportTopicLink.
        """
        link = ReportTopicLink(
            report_id=report_id,
            topic_id=topic_id,
            section_id=section_id,
            position=position,
            role=role,
            inclusion_reason=inclusion_reason,
            heat_score=heat_score,
            trend_score=trend_score,
        )
        self._session.add(link)
        await self._session.flush()
        return link

    def _to_dto(self, model: Report) -> ReportDTO:
        """Convert model to DTO."""
        sections = [
            ReportSectionDTO(**s) for s in (model.sections_json or [])
        ]

        return ReportDTO(
            id=model.id,
            report_type=model.report_type,
            report_date=model.report_date,
            title=model.title,
            executive_summary=model.executive_summary,
            sections=sections,
            topic_count=model.topic_count,
            generated_at=model.generated_at,
            status=model.status,
            metadata=model.metadata_json or {},
        )
